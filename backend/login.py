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

 
login_bp = Blueprint("login", __name__)
Notify = SMTPServer()

Config = load(open(BASE_DIR / "config" / "settings.json", encoding="utf-8"))

@login_bp.route("/", methods=["GET", "POST"])
def login():
    """
    Login screen.
        - GET:  Show the login form.
        - POST: Validate the name (2-10 chars), save to session, log the user,
            then redirect to the dashboard.
    """
    # Already logged in — skip straight to dashboard
    if "user" in session:
        return redirect(url_for("dashboard.dashboard"))
    global rfid_worker, _event_pending
    with _event_lock:
        _event_pending = None  # fresh page load — discard any stale pending event
    _stop_rfid.clear()  # always clear — keeps a dying worker alive, or lets a new one start
    if not rfid_worker.is_alive():
        rfid_worker = threading.Thread(target=rfid_polling_worker, daemon=True)
        rfid_worker.start()
    # Every time the page is loaded (GET), check the reader status
    """if request.method == "GET":
        print("[DEBUG] User accessed login screen. Checking RFID status...")
        if global_reader and global_reader.ping():
            print("[DEBUG] RFID Reader is online and responsive.")
            try:
                Notify.send_checked_in(database.get_tool_by_id(uid_info))
                print("Check-in alerts sent successfully.")
                    
            except Exception as e:
                print(f"Error sending check-in alerts: {e}")
        else:
            print("[DEBUG] RFID Reader offline. Attempting re-initialization...")
            # Optional: logic to try opening the port again if it dropped
 """
    error = None 
 
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower().capitalize()
 
        # Validate: 2–10 characters (matches design's TextBox validation)
        if len(username) < 2 or len(username) > 10:
            error = "Name must be between 2 and 10 characters."
        else:
            _stop_rfid.set()
            session["user"] = username
            database.log_user(username)
            if database.is_user_admin(username):
                session["is_admin"] = True
            return redirect(url_for("dashboard.dashboard"))
    
    return render_template("login.html", error=error)
 
 
 
 
_TAG_COOLDOWN = 5.0  # seconds to suppress re-processing the same tag

def rfid_polling_worker():
    while not _stop_rfid.is_set():
        last_uid = []
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
                        if uid == last_uid and (now - last_uid_at) < _TAG_COOLDOWN:
                            time.sleep(0.2)
                            continue
                        tool_id = rfid.read_block(4).rstrip(b'\x00').decode('ascii', errors='ignore').strip()
                        last_uid = uid
                        last_uid_at = time.monotonic()
                        if not tool_id:
                            _stop_rfid.wait(timeout=2.0)
                            continue
                        print(f"[SCAN] Tag detected on login screen: {tool_id}")
                        if tool_id.startswith('U'):
                            user = database.get_user_by_rfid(tool_id)
                            if user:
                                print(f'[DATABASE] User tag recognised: {user["name"]}')
                                _broadcast(("user-login", user["name"]))
                            else:
                                print(f'[DATABASE] No user registered for tag {tool_id}')
                        else:
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

_stop_rfid = threading.Event()
_event_lock = threading.Lock()
_event_pending = None

def _broadcast(event):
    global _event_pending
    with _event_lock:
        _event_pending = event

rfid_worker = threading.Thread(target=rfid_polling_worker, daemon=True)

@login_bp.route("/login/poll")
def login_poll():
    global _event_pending
    with _event_lock:
        event = _event_pending
        _event_pending = None
    if event is None:
        return ('', 204)
    kind, msg = event
    return jsonify(kind=kind, msg=msg)

@login_bp.route("/logout")
def logout():
    """
    Logout — triggered by the mdi-exit-to-app icon on the dashboard.
    Clears the session and returns to the login screen.
    """
    session.clear()
    return redirect(url_for("login.login"))
