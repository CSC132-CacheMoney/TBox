# login.py — login page, RFID polling worker, and logout

import os
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from alerts import SMTPServer
import database
from pico_Reader import RFIDBridge, RFIDBridgeError
import time
import threading
from pathlib import Path
from json import load
import dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
dotenv.load_dotenv()


def _load_settings():
    """Read and return the current settings.json contents."""
    with open(BASE_DIR / "config" / "settings.json", encoding="utf-8") as f:
        return load(f)


login_bp = Blueprint("login", __name__)
Notify   = SMTPServer()

# Config is loaded once at import time for the RFID worker's port setting
Config = load(open(BASE_DIR / "config" / "settings.json", encoding="utf-8"))


# ── Login route ────────────────────────────────────────────────────────────────

@login_bp.route("/", methods=["GET", "POST"])
def login():
    """Login screen.
    GET:  Show the name entry form; ensure the RFID polling worker is running.
    POST: Validate the name, handle admin-specific restrictions, and redirect
          to the dashboard on success."""
    # Already logged in — skip straight to dashboard
    if "user" in session:
        return redirect(url_for("dashboard.dashboard"))

    global rfid_worker, _event_pending
    # Discard any stale RFID event from a previous session load
    with _event_lock:
        _event_pending = None
    # Clear the stop flag so the worker can run; restart it if it has died
    _stop_rfid.clear()
    if not rfid_worker.is_alive():
        rfid_worker = threading.Thread(target=rfid_polling_worker, daemon=True)
        rfid_worker.start()

    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower().capitalize()

        if len(username) < 2 or len(username) > 10:
            error = "Name must be between 2 and 10 characters."

        elif database.is_user_admin(username) and request.form.get("_rfid_auth") != "1":
            # Admin accounts have stricter login rules depending on the client IP
            allowed_ips = _load_settings().get("rfid", {}).get("allowed_poll_ips", ["127.0.0.1", "::1"])

            if request.remote_addr in allowed_ips:
                # Trusted device (e.g. the kiosk): must use RFID card, no typing
                return render_template("login.html", error=None,
                                       toast_error="Admin accounts must log in with an RFID card.")
            else:
                # Remote device: allow password-based admin login instead
                admin_pw = request.form.get("_admin_password", "").strip()
                if not admin_pw:
                    # First POST — re-render with the password prompt visible
                    return render_template("login.html", show_password_prompt=True,
                                           prompt_username=username)
                if admin_pw != os.getenv("ADMIN_PASSWORD", ""):
                    return render_template("login.html", show_password_prompt=True,
                                           prompt_username=username,
                                           toast_error="Incorrect admin password.")
                # Password correct — complete the login
                _stop_rfid.set()
                session["user"]     = username
                session["is_admin"] = True
                database.log_user(username)
                return redirect(url_for("dashboard.dashboard"))

        else:
            # Normal (non-admin) login, or RFID-authenticated admin login
            _stop_rfid.set()
            session["user"] = username
            database.log_user(username)
            if database.is_user_admin(username):
                session["is_admin"] = True
            return redirect(url_for("dashboard.dashboard"))

    return render_template("login.html", error=error)


# ── RFID polling worker ────────────────────────────────────────────────────────

_TAG_COOLDOWN = 5.0  # seconds to suppress re-processing the same physical tag


def rfid_polling_worker():
    """Long-running daemon thread that continuously reads from the RFID reader
    while the login page is open.

    On each detected tag:
      - U-prefix IDs are user tags → broadcast a 'user-login' event.
      - All other IDs are tool tags → auto-return the tool and broadcast 'return'.

    last_uid / last_uid_at are reset inside the outer loop so the cooldown
    does not carry over after a reader reconnect."""
    while not _stop_rfid.is_set():
        # Reset cooldown on every (re)connect so stale UIDs don't block scans
        last_uid    = []
        last_uid_at = 0.0
        try:
            with RFIDBridge(Config['rfid']['port']) as rfid:
                if rfid.ping():
                    print('[RFID] Started')
                while not _stop_rfid.is_set():
                    try:
                        tag = rfid.scan()
                        uid = tag['uid']
                        now = time.monotonic()

                        # Skip the same physical tag within the cooldown window
                        if uid == last_uid and (now - last_uid_at) < _TAG_COOLDOWN:
                            time.sleep(0.2)
                            continue

                        # Read the payload written to block 4 (tool or user ID)
                        tool_id = rfid.read_block(4).rstrip(b'\x00').decode('ascii', errors='ignore').strip()
                        last_uid    = uid
                        last_uid_at = time.monotonic()

                        if not tool_id:
                            # Blank tag — nothing to act on
                            _stop_rfid.wait(timeout=2.0)
                            continue

                        print(f"[SCAN] Tag detected on login screen: {tool_id}")

                        if tool_id.startswith('U'):
                            # User login tag
                            user = database.get_user_by_rfid(tool_id)
                            if user:
                                print(f'[DATABASE] User tag recognised: {user["name"]}')
                                _broadcast(("user-login", user["name"]))
                            else:
                                print(f'[DATABASE] No user registered for tag {tool_id}')
                        else:
                            # Tool tag scanned at the login screen → auto-return
                            tool = database.get_tool_by_rfid(tool_id)
                            if tool:
                                database.return_tool(tool["id"])
                                print(f'[DATABASE] Tool returned: {tool["name"]}')
                                try:
                                    Notify.send_checked_in(tool["name"])
                                except Exception as e:
                                    print(f"[RFID] Alert failed: {e}")
                                _broadcast(("return", tool["name"]))
                            else:
                                print(f'[DATABASE] No valid tag {tool_id}!')

                        # Brief pause before accepting the next scan
                        _stop_rfid.wait(timeout=2.0)

                    except RFIDBridgeError as e:
                        if "No tag" in str(e):
                            time.sleep(0.2)
                            continue
                        raise

        except Exception as e:
            print(f"[RFID] Connection error: {e}")
            if not _stop_rfid.is_set():
                _broadcast(("error", "RFID reader disconnected — tap again to retry"))
                time.sleep(1)


# ── Event buffer and poll endpoint ────────────────────────────────────────────

_stop_rfid     = threading.Event()
_event_lock    = threading.Lock()
_event_pending = None   # holds the latest undelivered RFID event (kind, msg)


def _broadcast(event):
    """Store *event* so the next poll request can deliver it.
    Only the most recent event is kept; rapid successive scans overwrite each
    other, which is fine because each page load clears the buffer anyway."""
    global _event_pending
    with _event_lock:
        _event_pending = event


# Start the worker thread at import time so it's running when the first
# login page is served.  The login() GET handler will restart it if it dies.
rfid_worker = threading.Thread(target=rfid_polling_worker, daemon=True)


@login_bp.route("/login/poll")
def login_poll():
    """Short-poll endpoint called every 500 ms by the login page JS.
    Returns 204 (no content) when there is no pending event or when the
    client IP is not in the allowed list — remote clients see silence rather
    than an explicit rejection so they can still use the manual form."""
    global _event_pending

    # Only deliver RFID events to trusted IPs (kiosk / preset devices)
    allowed = _load_settings().get("rfid", {}).get("allowed_poll_ips", ["127.0.0.1", "::1"])
    if request.remote_addr not in allowed:
        # Return 204 without consuming the event so the kiosk can still get it
        return ('', 204)

    with _event_lock:
        event          = _event_pending
        _event_pending = None   # consume the event
    if event is None:
        return ('', 204)
    kind, msg = event
    return jsonify(kind=kind, msg=msg)


# ── Logout ─────────────────────────────────────────────────────────────────────

@login_bp.route("/logout")
def logout():
    """Clear the session and return to the login screen."""
    session.clear()
    return redirect(url_for("login.login"))
