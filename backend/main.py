import os
import threading
import time
from flask import Flask
from login import login_bp
from dashboard import dashboard_bp
from inventory import inventory_bp
from register import register_bp
from retire import retire_bp
import database
import webbrowser
from dotenv import load_dotenv
import alerts


load_dotenv()


def server():
    app = Flask(__name__, template_folder="../GUI/templates", static_folder="../GUI")
    app.secret_key = os.getenv("SECRET_KEY")
    if not os.path.exists("../TBox/data/tools.db"):
        database.init_db()
        print("Database initialized.")
    else:
        print("Database already exists. Skipping initialization.")

    app.register_blueprint(login_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(retire_bp)

    app.run(debug=False, host="0.0.0.0", port=6767)


def open_browser():
    time.sleep(1)
    webbrowser.open_new("http://localhost:6767")
    print("Browser opened to http://localhost:6767")


if __name__ == "__main__":
    threading.Thread(target=server, daemon=False).start()
    threading.Thread(target=alerts.initialize_alerts, daemon=True).start()
    threading.Thread(target=open_browser, daemon=True).start()
