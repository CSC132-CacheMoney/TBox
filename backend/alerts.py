# alerts.py
#
# Loki Nordstrom
# Aidan Southerland
# ------------------------------------------------


from smtplib import SMTP_SSL
from email.mime.text import MIMEText
from subprocess import run
from json import load
from pathlib import Path


# ------------------------------------------------


# SMTPServer class
class SMTPServer:
    
    
    """
    Core class that enables an SMTP server. It will then be
    capable of sending emails when items get checked in,
    checked out, registered, and retired.
    """
    
    
    # Constructor
    def __init__(self):
        # It is recommended to use gmail's SMTP hosting service
        # with port 465. Setting up our own SMTP server is not
        # feasible in the time we have left until the Expo.
        self.start("smtp.gmail.com", 465)
    
    
    # String overload
    def __str__(self):
        return super().__str__() + "\nSMTPServer object"
    
    
    # Alert.smtp
    @property
    def smtp(self): return self._smtp
    # --
    @smtp.setter
    def smtp(self, _smtp):
        if not isinstance(_smtp, SMTP_SSL):
            raise TypeError(f"Alert.smtp -> attempt to assign non-SMTP_SSL, {_smtp}: {type(_smtp)}")
        self._smtp = _smtp
    
    
    # Server methods
    def start(self, host: str, port: int):
        """Initialize the SMTP server."""
        
        try:
            _host = str(host)
            _port = int(port)
        except:
            raise TypeError(f"Could not pass 'host' or 'port' as intended types: {host}, {port}")
        self.smtp = SMTP_SSL(_host, _port) 
    
    # --
    
    def registered(self, toolName: str):
        """Send email on item registered."""
        
        msg = (
            f"An item: <{toolName}> has been registered to ToolVault.",
            "Tool Registered"
        )
        self.send(*msg)
    
    # --
    
    def checked_out(self, toolName: str):
        """Send email on item checked out."""
        
        msg = (
            f"An item: <{toolName}> has been checked out from ToolVault.",
            "Tool Checked Out"
        )
        self.send(*msg)
    
    # --
    
    def check_out_many(self, toolNames: list[str]):
        """
        Send email on several items checked out

        This function is specifically for inventory.checkout().
        """
        
        msg = (
            f"The following tools have been checked out: <{", ".join(toolNames)}>.",
            "Multiple Tools Checked Out"
        )
        self.send(*msg)
    
    # --
    
    def checked_in(self, toolName: str):
        """Send email on item checked in."""
        
        msg = (
            f"An item: <{toolName}> has been checked in to ToolVault.",
            "Tool Checked In"
        )
        self.send(*msg)
    
    # --
    
    def checked_in_many(self, toolNames: list[str]):
        """
        Send email on several items checked in.
        
        This function is specifically for inventory.return_tool().
        """
        
        msg = (
            f"The following tools have been checked in: <{", ".join(toolNames)}>.",
            "Multiple Tools Checked In"
        )
        self.send(*msg)
    
    # --
    
    def retired(self, toolName: str):
        """Send email on item retired."""
        
        msg = (
            f"A tool: <{toolName}> has been retired from ToolVault.",
            "Tool Retired"
        )
        self.send(*msg)
    
    # --
    
    def send(self, message: str, subject = ""):
        """Send emails."""
        
        try:
            _message = str(message)
            _subject = str(message)
        except:
            raise TypeError(f"Could not pass 'message' or 'subject' as strings: {message}, {message}")
        
        jsonRead = load(
            open(
                "config/settings.json",
                encoding = "utf-8"
            )
        )
        
        email = MIMEText(_message)
        email["Subject"] = _subject
        email["From"] = jsonRead["alerts"]["email_from"]
        email["To"] = jsonRead["alerts"]["email_to"]
        
        self.smtp.login(
            jsonRead["alerts"]["email_from"],
            jsonRead["alerts"]["email_app_password"]
        )
        self.smtp.send_message(email)
    
    # --
    
    def quit(self):
        """End SMTP server."""
        
        self.smtp.quit()


# ------------------------------------------------


# Function below for main.py (Southerland)
def initalerts():
    print("Initializing alerts system...")
    try:
        command = "python -m aiosmtpd -n -l 127.0.0.1:6969"
        run(command, shell = True, check = True)
        print("SMTP server started successfully.")
    except Exception as e:
        print(f"Error starting SMTP server: {e}")


# ------------------------------------------------


if __name__ != "__main__":
    if not Path("assets/cat.png").is_file():
        raise FileNotFoundError("The cat is missing...")
    server = SMTPServer()
