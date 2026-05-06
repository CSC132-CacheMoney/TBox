from flask import Blueprint, jsonify, session
import pico_Reader
from pico_Reader import RFIDBridge, RFIDBridgeError
import database
import threading
import time

settings_bp = Blueprint("settings", __name__)

_rfid_stop   = threading.Event()
_rfid_result = {"tag": None, "uid": None, "error": None}
_rfid_worker = threading.Thread()


def _user_rfid_write_worker(user_id: str):
    _rfid_result["tag"]   = None
    _rfid_result["uid"]   = None
    _rfid_result["error"] = None
    try:
        with RFIDBridge("/dev/ttyACM0") as rfid:
            while not _rfid_stop.is_set():
                try:
                    tag = rfid.scan()
                    rfid.write_block(4, user_id)
                    _rfid_result["tag"] = user_id
                    _rfid_result["uid"] = ":".join(f"{b:02X}" for b in tag["uid"])
                    break
                except RFIDBridgeError as e:
                    if "No tag" in str(e):
                        time.sleep(0.2)
                        continue
                    raise
    except Exception as e:
        print(f"[RFID SETTINGS] {e}")
        _rfid_result["error"] = "Reader disconnected — try again"


@settings_bp.route("/settings/rfid/init", methods=["POST"])
def settings_rfid_init():
    global _rfid_worker
    if "user" not in session:
        return jsonify({"success": False}), 401

    username = session["user"]

    existing_tag = database.get_user_rfid(username)
    if existing_tag:
        user_id = existing_tag
    else:
        all_tags = database.get_all_user_rfid_tags()
        user_id = pico_Reader.rand_User_ID()
        while user_id in all_tags:
            user_id = pico_Reader.rand_User_ID()
        database.set_user_rfid(username, user_id)

    _rfid_stop.set()
    if _rfid_worker.is_alive():
        _rfid_worker.join(timeout=2)
    _rfid_stop.clear()

    _rfid_worker = threading.Thread(target=_user_rfid_write_worker, args=(user_id,), daemon=True)
    _rfid_worker.start()
    return jsonify({"success": True, "user_id": user_id})


@settings_bp.route("/settings/rfid/poll")
def settings_rfid_poll():
    if "user" not in session:
        return jsonify({"tag": None}), 401
    return jsonify({
        "tag":   _rfid_result["tag"],
        "uid":   _rfid_result["uid"],
        "error": _rfid_result["error"],
    })


@settings_bp.route("/settings/user_rfid")
def get_user_rfid():
    if "user" not in session:
        return jsonify({"rfid_tag": None}), 401
    tag = database.get_user_rfid(session["user"])
    return jsonify({"rfid_tag": tag})
