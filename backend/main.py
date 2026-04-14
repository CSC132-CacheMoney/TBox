import os
import threading
from flask import Flask
from login import login_bp
from dashboard  import dashboard_bp
from inventory  import inventory_bp
from register  import register_bp
from retire  import retire_bp
import database
import webbrowser
import alerts as alert
from dotenv import load_dotenv  # Load environment variables from .env file
import time

load_dotenv()  # Load the .env file

def alerts():
    #threading.Thread(target=alert.initalerts).start()
    #threading.Thread(target=alert.test_alerts).start()
    print("Alerts system initialized.")
def open_browser():
    #Opens the localhost url, you can also acess it from the public url flask provides if you are on the same network.
    webbrowser.open_new("http://localhost:6767")
    print("Browser opened to http://localhost:6767")

#creates a Flask "Class", with arguments to change where it looks for the html and css files.

app = Flask(__name__, template_folder="../GUI/templates", static_folder="../GUI")
#Wont work without, create a .env file in the backend folder with a line like SECRET_KEY="XXXX"
app.secret_key = os.getenv("SECRET_KEY")  
#This checks if the database file exists, and if not it initializes it. This is important to ensure that the database doesnt get reset every time the server starts.
if not os.path.exists("../TBox/data"):
    database.init_db()  # Ensure DB is initialized on startup
    print("Database initialized.")
    #print (not os.path.exists("../TBox/data"), os.path.abspath("../TBox/data")) # Debugging line to check if the database file is created in the expected location.
    
else:
    print ("Database already exists. Skipping initialization.")
    #print (os.path.exists("../TBox/data"), os.path.abspath("../TBox/data")) # Debugging line to check if the database file exists in the expected location.

# Register route blueprints for flask. This allows us to organize our routes in separate files and keep the main file cleaner.
app.register_blueprint(login_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(register_bp)
app.register_blueprint(retire_bp)

if __name__ == "__main__":
    '''
    Starts the Flask app in a separate thread to allow another thread to open the browser.
    If you need to start another task such as alerts or RFID reading, you can start those 
    in additional threads here as well.
    '''
    threading.Thread(target=app.run, kwargs={'debug': False, 'host': "0.0.0.0", 'port': 6767}).start()
    time.sleep(5)
    threading.Thread(target=open_browser).start()  # Open the browser after the server starts
    time.sleep(3)
    threading.Thread(target=alerts).start()  # Start the alerts system in a separate thread (if implemented)

    
    


