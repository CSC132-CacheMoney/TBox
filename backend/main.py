# main.py — application entry point
# Wires together all Flask blueprints, initialises the database, and
# spawns background threads for the alert system and the auto browser-open.

import os
import threading
import time
from pathlib import Path
from flask import Flask
from login import login_bp
from dashboard import dashboard_bp
from inventory import inventory_bp
from register import register_bp
from retire import retire_bp
from settings import settings_bp
from admin import admin_bp
from summary import summary_bp
import database
import connections
import webbrowser
from dotenv import load_dotenv
import alerts


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()  # reads SECRET_KEY, ADMIN_PASSWORD, Proton_Mail_KEY from .env


def server():
    # Create the Flask app, pointing templates and static files at the GUI directory
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "GUI" / "templates"),
        static_folder=str(BASE_DIR / "GUI")
    )
    app.secret_key = os.getenv("SECRET_KEY")

    # Ensure all DB tables exist and apply any pending migrations
    database.init_db()
    print("Database ready.")

    # Track unique IPs in memory so new connections are only printed once
    _seen_ips = set()

    @app.before_request
    def _log_connection():
        # Runs before every route handler; keeps the live connections log current
        from flask import request, session
        ip = request.remote_addr
        connections.record(ip, session.get("user"))
        if ip not in _seen_ips:
            _seen_ips.add(ip)
            print(f"[NET] New connection from {ip}")

    # Register every feature blueprint
    app.register_blueprint(login_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(retire_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(summary_bp)

    # Bind to all interfaces so LAN and remote clients can connect
    app.run(debug=False, host="0.0.0.0", port=6767)


def open_browser():
    # Small delay so Flask finishes binding the port before the browser hits it
    time.sleep(1)
    webbrowser.open_new("http://localhost:6767")
    print("Browser opened to http://localhost:6767")


if __name__ == "__main__":
    # server is non-daemon so the process stays alive; other threads are daemon
    threading.Thread(target=server, daemon=False).start()
    threading.Thread(target=alerts.initialize_alerts, daemon=True).start()
    threading.Thread(target=open_browser, daemon=True).start()
