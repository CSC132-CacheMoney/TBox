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
import webbrowser
from dotenv import load_dotenv
import alerts


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()


def server():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "GUI" / "templates"),
        static_folder=str(BASE_DIR / "GUI")
    )
    app.secret_key = os.getenv("SECRET_KEY")
    database.init_db()
    print("Database ready.")

    app.register_blueprint(login_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(retire_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(summary_bp)

    app.run(debug=False, host="0.0.0.0", port=6767)


def open_browser():
    time.sleep(1)
    webbrowser.open_new("http://localhost:6767")
    print("Browser opened to http://localhost:6767")


if __name__ == "__main__":
    threading.Thread(target=server, daemon=False).start()
    threading.Thread(target=alerts.initialize_alerts, daemon=True).start()
    threading.Thread(target=open_browser, daemon=True).start()
