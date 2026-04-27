from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response
from alerts import SMTPServer
import database
from pico_Reader import RFIDBridge, RFIDBridgeError
import time
import threading
import queue

 
login_bp = Blueprint("login", __name__)
Notify = SMTPServer()
 
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
    global rfid_worker
    if not rfid_worker.is_alive():
        _stop_rfid.clear()
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
            return redirect(url_for("dashboard.dashboard"))
    
    return render_template("login.html", error=error)
 
 
 
 
def rfid_polling_worker():
    with RFIDBridge("/dev/ttyACM0") as rfid:
        try:
            response = rfid.ping()
            if response:
                print ('[RFID] Started')
                
        except:
            print ('[RFID] err')
            
        while not _stop_rfid.is_set():
            try:
                tag_UID = rfid.scan()
                print("UID:", tag_UID['uid'])
                tool_id = rfid.read_block(4).rstrip(b'\x00').decode()
                if tool_id:
                    print(f"[SCAN] Tag detected on login screen: {tool_id}")
                    tool = database.get_tool_by_rfid(tool_id)
                    if tool:
                        database.return_tool(tool["id"])
                        print(f'[DATABASE] Tool returned: {tool["name"]}')
                        Notify.send_checked_in(tool["name"])
                        _toast_queue.put(tool["name"])
                    else:
                        print(f'[DATABASE] No valid tag {tool_id}!')
                    time.sleep(2)
            except RFIDBridgeError as e:
                if "No tag" in str(e):
                    time.sleep(0.2)
                    continue
                raise

_stop_rfid = threading.Event()
_toast_queue: queue.SimpleQueue = queue.SimpleQueue()
rfid_worker = threading.Thread(target=rfid_polling_worker, daemon=True)

@login_bp.route("/login/events")
def login_events():
    def stream():
        while True:
            try:
                name = _toast_queue.get(timeout=25)
                yield f"data: {name}\n\n"
            except queue.Empty:
                yield ": keepalive\n\n"
    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@login_bp.route("/logout")
def logout():
    """
    Logout — triggered by the mdi-exit-to-app icon on the dashboard.
    Clears the session and returns to the login screen.
    """
    session.clear()
    return redirect(url_for("login.login"))
