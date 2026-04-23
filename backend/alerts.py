# alerts.py
#
# Created by:
# Loki Nordstrom
# Optimized by:
# Aidan Southerland
# ------------------------------------------------
import os
import smtplib
from email.mime.text import MIMEText
from json import load
from pathlib import Path
import dotenv

dotenv.load_dotenv()
Config = load(open("config/settings.json", encoding="utf-8"))

class SMTPServer:
    def __init__(self,
                host=Config["alerts"]["email_host"],
                port=Config["alerts"]["email_port"],
                recipiant=Config["alerts"]["email_to"],
                username=Config["alerts"]["email_from"],
                password=None):
        self.SMTP_HOST = host
        self.SMTP_PORT = port
        self.TO = recipiant
        self.USERNAME = username
        self.PASSWORD = password or os.getenv("Proton_Mail_KEY")
        self._smtp = None
# Operator overload for debug
    def __str__(self):
        return f"SMTPServer({self.SMTP_HOST}:{self.SMTP_PORT} user={self.USERNAME})"
 # Connect to the SMTP server and log in. This is done lazily when the first email is sent to avoid unnecessary connections if no alerts are triggered.
    def _connect(self):
        if self._smtp:
            return
        if not (self.USERNAME and self.PASSWORD):
            raise RuntimeError("Missing SMTP username or password")
        smtp = smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT, timeout=30)
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(self.USERNAME, self.PASSWORD)
        self._smtp = smtp
# Disconnect from the SMTP server when the object is deleted to ensure we don't leave open connections.
    def _disconnect(self):
        if self._smtp:
            try:
                self._smtp.quit()
            except Exception:
                try: self._smtp.close()
                except Exception: pass
            self._smtp = None
# Basic function to send an email, used by the more specific functions below. You can also use this directly if you want to send a custom notification.
    def _send(self, body: str, subject: str, from_addr: str = None, to_addrs=None):
        from_addr = from_addr or self.USERNAME
        to_addrs = to_addrs or [self.TO]
        if not self._smtp:
            self._connect()
        email = MIMEText(body)
        email["Subject"] = subject
        email["From"] = from_addr
        email["To"] = ", ".join(to_addrs)
        self._smtp.send_message(email, from_addr=from_addr, to_addrs=to_addrs)

# ------------------------------------------------

    def send_registered(self, toolName: str):
        self._send(f"An item: <{toolName}> has been registered to ToolVault.", "Tool Registered")

    def send_checked_out(self, toolName: str):
        self._send(f"An item: <{toolName}> has been checked out from ToolVault.", "Tool Checked Out")

    def send_checked_in(self, toolName: str):
        self._send(f"An item: <{toolName}> has been checked in to ToolVault.", "Tool Returned")

    def send_retired(self, toolName: str):
        self._send(f"A tool: <{toolName}> has been retired from ToolVault.", "Tool Retired")

# ------------------------------------------------
def initialize_alerts():
    """Initialize the alerts system."""
    try:
        smtp_server = SMTPServer()
        smtp_server._connect()
        print("Alerts system initialized successfully.")
        return smtp_server
    except Exception as e:
        print(f"Error initializing alerts system: {e}")
        return None

# ------------------------------------------------


if __name__ == "__main__":
    if not Path("assets/cat.png").is_file():
        raise FileNotFoundError("The cat is missing...")
    Notifications = initialize_alerts()
    Notifications.send_registered("Example Tool")
    Notifications.send_checked_out("Example Tool")
    Notifications.send_checked_in("Example Tool")
    Notifications.send_retired("Example Tool")
    
    
    
    
    ''' msg = EmailMessage()
    msg["From"] = USERNAME
    msg["To"] = TO
    msg["Subject"] = "Test via Proton SMTP"
    msg.set_content("Hello — sent via direct Proton SMTP with token.")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(USERNAME, SMTP_PASS)
        smtp.ehlo()
        smtp.send_message(msg)'''
    #server = SMTPServer()
    #server.registered("Example Tool")
