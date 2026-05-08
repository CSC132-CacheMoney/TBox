# register.py — tool registration with optional RFID tag writing (admin only)

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import pico_Reader
from pico_Reader import RFIDBridge, RFIDBridgeError
import database
import alerts
import threading
import time
from pathlib import Path
from json import load

BASE_DIR = Path(__file__).resolve().parent.parent
Config   = load(open(BASE_DIR / "config" / "settings.json", encoding="utf-8"))

register_bp = Blueprint("register", __name__)

# Module-level RFID write state — one write job can be active at a time
_rfid_stop   = threading.Event()
_rfid_result = {"tag": None, "uid": None, "error": None}
_rfid_worker = threading.Thread()


def _rfid_write_worker(tool_id: str):
    """Background thread: waits for an RFID tag to be presented, then writes
    *tool_id* to block 4.  Polls at 200 ms intervals to stay responsive to
    the stop event without spinning the CPU."""
    _rfid_result["tag"]   = None
    _rfid_result["uid"]   = None
    _rfid_result["error"] = None
    try:
        with RFIDBridge(Config['rfid']['port']) as rfid:
            while not _rfid_stop.is_set():
                try:
                    tag = rfid.scan()
                    rfid.write_block(4, tool_id)
                    _rfid_result["tag"] = tool_id
                    # Format UID as colon-separated hex for display
                    _rfid_result["uid"] = ":".join(f"{b:02X}" for b in tag["uid"])
                    break
                except RFIDBridgeError as e:
                    if "No tag" in str(e):
                        time.sleep(0.2)
                        continue
                    raise
    except Exception as e:
        print(f"[RFID REGISTER] {e}")
        _rfid_result["error"] = "Reader disconnected — try again"


@register_bp.route("/register/rfid/init", methods=["POST"])
def register_rfid_init():
    """Start a new RFID write job for a freshly generated unique tool ID.
    Cancels any in-progress write first."""
    global _rfid_worker
    if "user" not in session:
        return jsonify({"success": False}), 401
    if not session.get("is_admin"):
        return jsonify({"success": False}), 403

    # Generate a tool ID that doesn't collide with any existing tag
    existing = {dict(r)["rfid_tag"] for r in database.get_all_tools() if dict(r).get("rfid_tag")}
    tool_id  = pico_Reader.rand_Tool_ID()
    while tool_id in existing:
        tool_id = pico_Reader.rand_Tool_ID()

    # Stop any running worker before starting a new one
    _rfid_stop.set()
    if _rfid_worker.is_alive():
        _rfid_worker.join(timeout=2)
    _rfid_stop.clear()

    _rfid_worker = threading.Thread(target=_rfid_write_worker, args=(tool_id,), daemon=True)
    _rfid_worker.start()
    return jsonify({"success": True})


@register_bp.route("/register/rfid/poll")
def register_rfid_poll():
    """Poll the result of the current RFID write job.  The frontend calls
    this every 400 ms until tag or error is set."""
    if "user" not in session:
        return jsonify({"tag": None}), 401
    if not session.get("is_admin"):
        return jsonify({"tag": None}), 403
    return jsonify({
        "tag":   _rfid_result["tag"],
        "uid":   _rfid_result["uid"],
        "error": _rfid_result["error"],
    })


@register_bp.route("/register", methods=["GET", "POST"])
def register_tool():
    """Tool registration form — admin only.
    GET:  Show the registration form.
    POST: Validate input, write the tool to the database, and send an alert."""
    if "user" not in session:
        return redirect(url_for("login.login"))
    if not session.get("is_admin"):
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        tool_name = request.form.get("tool_name", "").strip().lower().capitalize()
        condition = request.form.get("condition", "Good")
        category  = request.form.get("category",  "Hand Tool")
        brand     = request.form.get("brand", "").strip()
        rfid_tag  = request.form.get("rfid_tag") or None  # None triggers auto-generation in DB

        if not tool_name:
            flash("Please enter a tool name.", "error")
            return render_template("register.html", condition=condition, category=category)

        try:
            database.register_tool(
                name=tool_name,
                rfid_tag=rfid_tag,
                category=category,
                condition=condition,
                brand=brand,
            )
            label = database.display_name({"name": tool_name, "brand": brand})
            flash(f"'{label}' registered successfully.", "success")
            # Alert email sent in background to avoid blocking the redirect
            threading.Thread(target=alerts.server.send_registered, args=(label,), daemon=True).start()
            return redirect(url_for("register.register_tool"))

        except ValueError as e:
            flash(str(e), "error")

    return render_template("register.html")
