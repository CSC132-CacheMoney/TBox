# alerts.py
#
# Loki Darius Edullantes Nordstrom
# Several tinkers by Aidan Southerland
# ------------------------------------------------


from smtplib import SMTP_SSL
from email.mime.text import MIMEText
from subprocess import run
from json import load


# ------------------------------------------------


# SMTPServer class
class SMTPServer:
    
    
    """
    Core class that enables an SMTP server so that emails can
    be sent out as alerts to when items get checked in, checked
    out, registered, and retired.
    """
    
    
    # Constructor
    def __init__(self):
        self.start("smtp.gmail.com", 465)
    
    
    # String overload
    def __str__(self):
        return "SMTPServer object"
    
    
    # Alert.smtp
    @property
    def smtp(self):
        return self._smtp
    # --
    @smtp.setter
    def smtp(self, smtp):
        if not isinstance(smtp, SMTP_SSL):
            return
        self._smtp = smtp
    
    
    # Server methods
    def start(self, host: str, port: int):
        """Initialize the SMTP server."""
        #  ---------------------------
        if not isinstance(host, str):
            return
        elif not isinstance(port, int):
            return
        self.smtp = SMTP_SSL(host, port) 
    
    # --
    
    def registered(self, toolName: str):
        """Send email on item registered."""
        #  ------------------------------
        msg = (
            f"An item: <{toolName}> has been registered to ToolVault.",
            "Tool Registered"
        )
        self.send(*msg)
    
    # --
    
    def checked_out(self, toolName: str):
        """Send email on item checked out."""
        #  -------------------------------
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
        #  ---------------------------------------
        msg = (
            f"The following tools have been checked out: <{", ".join(toolNames)}>.",
            "Multiple Tools Checked Out"
        )
        self.send(*msg)
    
    # --
    
    def checked_in(self, toolName: str):
        """Send email on item checked in."""
        #  ------------------------------
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
        # -------------------------------------------------------
        msg = (
            f"The following tools have been checked in: <{", ".join(toolNames)}>.",
            "Multiple Tools Checked In"
        )
        self.send(*msg)
    
    # --
    
    def retired(self, toolName: str):
        """Send email on item retired."""
        #  ---------------------------
        msg = (
            f"A tool: <{toolName}> has been retired from ToolVault.",
            "Tool Retired"
        )
        self.send(*msg)
    
    # --
    
    def send(self, message: str, subject = ""):
        """Send emails."""
        #  ------------
        if not isinstance(message, str):
            return
        elif not isinstance(subject, str):
            return
        
        jsonRead = load(
            open(
                "../config/settings.json",
                "r",
                encoding = "utf-8"
            )
        )
        
        email = MIMEText(message)
        email["Subject"] = subject
        email["From"] = jsonRead["alerts"]["email_from"]
        email["To"] = jsonRead["alerts"]["email_to"]
        
        self.smtp.login(
            jsonRead["alerts"]["email_target"],
            "intentionallyIncorrectAppPassword"
        )
        self.smtp.send_message(email)
    
    # --
    
    def quit(self):
        """End SMTP server."""
        #  ----------------
        self.smtp.quit()


# ------------------------------------------------


# Function below for main.py (Southerland)
def initalerts():
    print("Initializing alerts system...")
    try:
        command = "python -m aiosmtpd -n -l 127.0.0.1:6969"
        run(command, shell=True, check=True)
        print("SMTP server started successfully.")
    except Exception as e:
        print(f"Error starting SMTP server: {e}")


# ------------------------------------------------


if __name__ == "__main__":
    print("Running alerts.py as __main__. Please run main.py, instead.")
else:
    server = SMTPServer()
