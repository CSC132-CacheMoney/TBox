# admin.py — admin panel: settings, checkouts, user management, RFID assignment

import os
import json
import threading
import time
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import database
import connections
import pico_Reader
from pico_Reader import RFIDBridge, RFIDBridgeError

admin_bp = Blueprint("admin", __name__)

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.json"

# Module-level state for the user RFID assignment worker
_ua_lock   = threading.Lock()
_ua_stop   = threading.Event()
_ua_result = {"done": False, "tag": None, "error": None}
_ua_worker = threading.Thread()


def _assign_rfid_worker(username: str, user_tag: str, port: str):
    """Background thread: waits for an RFID tag, writes *user_tag* to block 4,
    then persists the mapping in the database.  Resets result state on entry
    so stale values from a prior run are never returned."""
    with _ua_lock:
        _ua_result["done"]  = False
        _ua_result["tag"]   = None
        _ua_result["error"] = None
    try:
        with RFIDBridge(port) as rfid:
            while not _ua_stop.is_set():
                try:
                    rfid.scan()
                    rfid.write_block(4, user_tag)
                    database.set_user_rfid(username, user_tag)
                    with _ua_lock:
                        _ua_result["done"] = True
                        _ua_result["tag"]  = user_tag
                    return
                except RFIDBridgeError as e:
                    if "No tag" in str(e):
                        time.sleep(0.2)
                        continue
                    raise
    except Exception as e:
        with _ua_lock:
            _ua_result["error"] = str(e)


def _load_settings():
    """Read and return the settings.json file."""
    with open(SETTINGS_PATH) as f:
        return json.load(f)


def _save_settings(data):
    """Write *data* to settings.json, overwriting the existing contents."""
    with open(SETTINGS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _is_admin():
    """Return True if the current session has admin privileges.
    Caches the result in the session to avoid a DB hit on every request."""
    if session.get("is_admin"):
        return True
    if "user" in session and database.is_user_admin(session["user"]):
        session["is_admin"] = True
        return True
    return False


# ── Authentication ─────────────────────────────────────────────────────────────

@admin_bp.route("/admin/auth", methods=["POST"])
def admin_auth():
    """Verify the admin password submitted from the settings cogwheel modal.
    Requires the user to already have an RFID card assigned — this prevents
    account takeover if the password leaks but no physical card is present."""
    if "user" not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 401
    if not database.get_user_rfid(session["user"]):
        return jsonify({"success": False, "error": "You must have an RFID card assigned before gaining admin access."})

    password       = request.form.get("password", "")
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if not admin_password:
        return jsonify({"success": False, "error": "No ADMIN_PASSWORD configured in .env"})
    if password == admin_password:
        session["is_admin"] = True
        database.set_admin(session["user"], True)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Incorrect password"})


# ── Main panel ─────────────────────────────────────────────────────────────────

@admin_bp.route("/admin")
def admin_panel():
    """Render the admin panel with all data sections pre-loaded."""
    if "user" not in session:
        return redirect(url_for("login.login"))
    if not _is_admin():
        return redirect(url_for("dashboard.dashboard"))

    checked_out = database.get_checked_out_tools()
    settings    = _load_settings()
    users       = database.get_all_users()
    return render_template("admin.html", checked_out=checked_out, settings=settings,
                           users=users, current_ip=request.remote_addr)


# ── Settings ───────────────────────────────────────────────────────────────────

@admin_bp.route("/admin/settings", methods=["POST"])
def admin_save_settings():
    """Parse and persist the settings form.  All fields are validated/coerced
    here rather than relying on the browser so the JSON file stays well-formed."""
    if "user" not in session or not _is_admin():
        return redirect(url_for("admin.admin_panel"))

    try:
        # Parse allowed IPs as one-per-line; fall back to localhost if the
        # textarea is left blank to avoid accidentally locking everyone out
        raw_ips     = request.form.get("rfid_allowed_ips", "127.0.0.1\n::1")
        allowed_ips = [ip.strip() for ip in raw_ips.splitlines() if ip.strip()] or ["127.0.0.1", "::1"]

        new_settings = {
            "rfid": {
                "port":             request.form.get("rfid_port", "").strip(),
                "allowed_poll_ips": allowed_ips,
            },
            "alerts": {
                "checkout_limit_hours": int(request.form.get("checkout_limit_hours", 24)),
                "email_host":           request.form.get("email_host", "").strip(),
                "email_port":           int(request.form.get("email_port", 587)),
                "alert_method":         request.form.get("alert_method", "console"),
                "email_from":           request.form.get("email_from", "").strip(),
                "email_to":             request.form.get("email_to", "").strip(),
            },
            "database": {
                "path": request.form.get("db_path", "data/tools.db").strip()
            }
        }
        _save_settings(new_settings)
        flash("Settings saved successfully.", "success")
    except (ValueError, OSError) as e:
        flash(f"Failed to save settings: {e}", "error")

    return redirect(url_for("admin.admin_panel") + "#settings")


# ── Checkout management ────────────────────────────────────────────────────────

@admin_bp.route("/admin/return/<int:tool_id>", methods=["POST"])
def admin_return_tool(tool_id):
    """Force-return a checked-out tool without requiring a physical RFID scan."""
    if "user" not in session or not _is_admin():
        return redirect(url_for("admin.admin_panel"))

    tool = database.get_tool_by_id(tool_id)
    if tool:
        database.return_tool(tool_id)
        flash(f"'{database.display_name(dict(tool))}' marked as returned.", "success")
    else:
        flash("Tool not found.", "error")

    return redirect(url_for("admin.admin_panel") + "#checkouts")


# ── Danger zone ────────────────────────────────────────────────────────────────

@admin_bp.route("/admin/reset", methods=["POST"])
def admin_reset_db():
    """Wipe the entire database and redirect to the login screen.
    Session is cleared so the admin must log in again after the reset."""
    if "user" not in session or not _is_admin():
        return redirect(url_for("admin.admin_panel"))

    database.reset_database()
    session.clear()
    flash("Database has been reset. All tools and records have been cleared.", "success")
    return redirect(url_for("login.login"))


# ── User RFID assignment ───────────────────────────────────────────────────────

@admin_bp.route("/admin/user_rfid/assign", methods=["POST"])
def admin_user_rfid_assign():
    """Generate a unique user tag ID and start the RFID write worker for the
    specified username.  Any in-progress write is cancelled first."""
    global _ua_worker
    if "user" not in session or not _is_admin():
        return jsonify({"success": False, "error": "Not authorised"}), 403

    username = request.json.get("username", "").strip()
    if not username:
        return jsonify({"success": False, "error": "No username provided"})

    settings = _load_settings()
    port     = settings.get("rfid", {}).get("port", "/dev/ttyACM0")

    # Generate a tag ID that doesn't collide with any existing user tag
    all_tags = database.get_all_user_rfid_tags()
    user_tag = pico_Reader.rand_User_ID()
    while user_tag in all_tags:
        user_tag = pico_Reader.rand_User_ID()

    # Stop any running worker before starting a new one
    _ua_stop.set()
    if _ua_worker.is_alive():
        _ua_worker.join(timeout=2)
    _ua_stop.clear()

    _ua_worker = threading.Thread(
        target=_assign_rfid_worker, args=(username, user_tag, port), daemon=True
    )
    _ua_worker.start()
    return jsonify({"success": True})


@admin_bp.route("/admin/user_rfid/poll")
def admin_user_rfid_poll():
    """Poll the result of the current user RFID assignment job."""
    if "user" not in session or not _is_admin():
        return jsonify({}), 403
    with _ua_lock:
        return jsonify(dict(_ua_result))


@admin_bp.route("/admin/user_rfid/cancel", methods=["POST"])
def admin_user_rfid_cancel():
    """Cancel an in-progress user RFID assignment."""
    if "user" not in session or not _is_admin():
        return jsonify({}), 403
    _ua_stop.set()
    return jsonify({"success": True})


# ── Admin grant / revoke ───────────────────────────────────────────────────────

@admin_bp.route("/admin/set_admin", methods=["POST"])
def admin_set_admin():
    """Grant or revoke admin status for another user.
    Rules enforced here (mirrored in the template UI):
      - Cannot change your own status.
      - Cannot grant admin without an RFID tag assigned (physical-card
        requirement prevents lockout if the password is compromised)."""
    if "user" not in session or not _is_admin():
        return jsonify({"success": False, "error": "Not authorised"}), 403

    data     = request.json or {}
    username = data.get("username", "").strip()
    grant    = bool(data.get("grant", False))

    if not username:
        return jsonify({"success": False, "error": "No username provided"})
    if username == session["user"]:
        return jsonify({"success": False, "error": "You cannot change your own admin status"})
    if grant and not database.get_user_rfid(username):
        return jsonify({"success": False, "error": "User must have an RFID tag before being granted admin"})

    database.set_admin(username, grant)
    return jsonify({"success": True})


# ── Connected clients ──────────────────────────────────────────────────────────

@admin_bp.route("/admin/connections")
def admin_connections_api():
    """Return the live connections log as JSON for the admin panel table."""
    if "user" not in session or not _is_admin():
        return jsonify([]), 403
    return jsonify(connections.get_all())
