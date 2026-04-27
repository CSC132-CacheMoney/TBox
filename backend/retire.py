from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import database
import alerts
import threading
import time
from pico_Reader import RFIDBridge, RFIDBridgeError

retire_bp = Blueprint("retire", __name__)

_rfid_stop   = threading.Event()
_rfid_result = {"tag": None}   # written by worker, read by poll endpoint
_rfid_worker = threading.Thread()


def _rfid_write_worker(tag_to_write: str):
    _rfid_result["tag"] = None
    try:
        with RFIDBridge("/dev/ttyACM0") as rfid:
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


@retire_bp.route("/rfid/init", methods=["POST"])
def rfid_init():
    global _rfid_worker
    if "user" not in session:
        return jsonify({"success": False}), 401

    rfid_tag = (request.json or {}).get("rfid_tag", "")
    if not rfid_tag:
        return jsonify({"success": False, "msg": "no rfid_tag provided"}), 400

    _rfid_stop.set()
    if _rfid_worker.is_alive():
        _rfid_worker.join(timeout=2)

    _rfid_stop.clear()
    _rfid_worker = threading.Thread(target=_rfid_write_worker, args=(rfid_tag,), daemon=True)
    _rfid_worker.start()
    return jsonify({"success": True})


@retire_bp.route("/rfid/poll")
def rfid_poll():
    if "user" not in session:
        return jsonify({"tag": None}), 401
    return jsonify({"tag": _rfid_result["tag"]})


@retire_bp.route("/replace", methods=["POST"])
def replace_tool():
    if "user" not in session:
        return redirect(url_for("login.login"))
    _rfid_stop.set()
    tool_id = request.form.get("tool_id", "")
    tool = database.get_tool_by_id(int(tool_id)) if tool_id.isdigit() else None
    if tool:
        flash(f"RFID tag replaced for '{tool['name']}'.", "success")
    else:
        flash("Tool not found.", "error")
    return redirect(url_for("inventory.inventory"))


@retire_bp.route("/retire", methods=["GET", "POST"])
def retire_tool():
    """
    Retire Tool screen (s10071).
    - GET:  Show the list of active (non-retired) tools to choose from.
    - POST: Mark selected tool(s) as Retired in the database.
            Retired tools stay in the DB for checkout history records.
    """
    if "user" not in session:
        return redirect(url_for("login.login"))

    if request.method == "POST":
        raw = request.form.get("tool_id", "")
        tool_ids = [int(i) for i in raw.split(",") if i.strip().isdigit()]

        if not tool_ids:
            flash("No tools selected.", "error")
            return redirect(url_for("retire.retire_tool"))

        retired_name = ""
        for tool_id in tool_ids:
            tool = database.get_tool_by_id(tool_id)
            if tool:
                # Don't retire a tool that's currently checked out
                if tool["status"] == "Checked Out":
                    flash(
                        f"'{tool['name']}' is currently checked out and cannot be retired.",
                        "error"
                    )
                    continue
                database.retire_tool(tool_id)
                retired_name = tool['name']

        if retired_name:
            flash(
                f"Tool retired: {retired_name}.",
                "success"
            )
            alerts.server.retired(retired_name)

        return redirect(url_for("inventory.inventory"))

    # GET — load all tools that can be retired (not already retired)
    tools = [dict(row) for row in database.get_active_tools()]

    return render_template("retire.html", tools=tools)