# retire.py — tool retirement and RFID tag replacement (admin only)

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import database
import alerts
import threading
import time
from pico_Reader import RFIDBridge, RFIDBridgeError
from pathlib import Path
from json import load

BASE_DIR = Path(__file__).resolve().parent.parent
Config   = load(open(BASE_DIR / "config" / "settings.json", encoding="utf-8"))

retire_bp = Blueprint("retire", __name__)

# Module-level RFID write state — one write job active at a time
_rfid_stop   = threading.Event()
_rfid_result = {"tag": None, "error": None}
_rfid_worker = threading.Thread()


def _rfid_write_worker(tag_to_write: str):
    """Background thread: waits for an RFID tag, then overwrites block 4
    with *tag_to_write*.  Used when replacing a damaged or lost tag."""
    _rfid_result["tag"]   = None
    _rfid_result["error"] = None
    try:
        with RFIDBridge(Config['rfid']['port']) as rfid:
            while not _rfid_stop.is_set():
                try:
                    rfid.scan()
                    rfid.write_block(4, tag_to_write)
                    _rfid_result["tag"] = tag_to_write
                    break
                except RFIDBridgeError as e:
                    if "No tag" in str(e):
                        time.sleep(0.2)
                        continue
                    raise
    except Exception as e:
        print(f"[RFID WRITE] {e}")
        _rfid_result["error"] = "Reader disconnected — initialize and try again"


@retire_bp.route("/rfid/init", methods=["POST"])
def rfid_init():
    """Start an RFID write job for the tag ID supplied in the JSON body.
    Cancels any in-progress write first."""
    global _rfid_worker
    if "user" not in session:
        return jsonify({"success": False}), 401
    if not session.get("is_admin"):
        return jsonify({"success": False}), 403

    rfid_tag = (request.json or {}).get("rfid_tag", "")
    if not rfid_tag:
        return jsonify({"success": False, "msg": "no rfid_tag provided"}), 400

    # Stop any running worker before starting a fresh one
    _rfid_stop.set()
    if _rfid_worker.is_alive():
        _rfid_worker.join(timeout=2)

    _rfid_stop.clear()
    _rfid_worker = threading.Thread(target=_rfid_write_worker, args=(rfid_tag,), daemon=True)
    _rfid_worker.start()
    return jsonify({"success": True})


@retire_bp.route("/rfid/poll")
def rfid_poll():
    """Poll the result of the current RFID write job."""
    if "user" not in session:
        return jsonify({"tag": None}), 401
    if not session.get("is_admin"):
        return jsonify({"tag": None}), 403
    return jsonify({"tag": _rfid_result["tag"], "error": _rfid_result["error"]})


@retire_bp.route("/replace", methods=["POST"])
def replace_tool():
    """Handle the tag-replacement form submission — stops the write worker
    and redirects back to inventory."""
    if "user" not in session:
        return redirect(url_for("login.login"))
    if not session.get("is_admin"):
        return redirect(url_for("dashboard.dashboard"))
    _rfid_stop.set()
    tool_id = request.form.get("tool_id", "")
    tool    = database.get_tool_by_id(int(tool_id)) if tool_id.isdigit() else None
    if tool:
        flash(f"RFID tag replaced for '{tool['name']}'.", "success")
    else:
        flash("Tool not found.", "error")
    return redirect(url_for("inventory.inventory"))


@retire_bp.route("/retire", methods=["GET", "POST"])
def retire_tool():
    """Retire Tool page — admin only.
    GET:  Show a list of active (non-retired) tools.
    POST: Mark selected tools as Retired.  Retired tools are kept in the
          database so checkout history is preserved."""
    if "user" not in session:
        return redirect(url_for("login.login"))
    if not session.get("is_admin"):
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        raw      = request.form.get("tool_id", "")
        tool_ids = [int(i) for i in raw.split(",") if i.strip().isdigit()]

        if not tool_ids:
            flash("No tools selected.", "error")
            return redirect(url_for("retire.retire_tool"))

        retired_name = ""
        for tool_id in tool_ids:
            tool = database.get_tool_by_id(tool_id)
            if tool:
                # Prevent retiring a tool that is currently checked out
                if tool["status"] == "Checked Out":
                    flash(
                        f"'{tool['name']}' is currently checked out and cannot be retired.",
                        "error"
                    )
                    continue
                database.retire_tool(tool_id)
                retired_name = database.display_name(dict(tool))

        if retired_name:
            flash(f"Tool retired: {retired_name}.", "success")
            threading.Thread(target=alerts.server.send_retired, args=(retired_name,), daemon=True).start()

        return redirect(url_for("inventory.inventory"))

    # GET — load all tools that can still be retired
    tools = [dict(row) for row in database.get_active_tools()]
    return render_template("retire.html", tools=tools)
