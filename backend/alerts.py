# alerts.py
#
# Loki Darius Edullantes Nordstrom
# Several tinkers by Aidan Southerland
# ------------------------------------------------


from smtplib import SMTP_SSL
# from time import sleep
# import aiosmtpd as server
from email.mime.text import MIMEText
from subprocess import run
from json import load


# ------------------------------------------------


# SMTPServer class
class SMTPServer:
    # Constructor
    def __init__(self):
        self.start("smtp.gmail.com", 465)
    
    
    # String overload
    def __str__(self):
        return "Alert object"
    
    
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
    
    
    # server methods
    def start(self, host: str, port: int):
        if not isinstance(host, str):
            return
        elif not isinstance(port, int):
            return
        self.smtp = SMTP_SSL(host, port) 
    # --
    def registered(self, toolName: str):
        self.send(
            f"An item: <{toolName}> has been registered to ToolVault.",
            "Tool Registered"
        )
    # --
    def checked_out(self, toolName: str):
        self.send(
            f"An item: <{toolName}> has been checked out from ToolVault.",
            "Tool Checked Out"
        )
    # --
    def checked_in(self, toolName: str):
        self.send(
            f"An item: <{toolName}> has been checked in to ToolVault.",
            "Tool Checked In"
        )
    # --
    def retired(self, toolName: str):
        self.send(
            f"A tool: <{toolName}> has been retired from ToolVault.",
            "Tool Retired"
        )
    # --
    def send(self, message: str, subject = ""):
        if not isinstance(message, str):
            return
        elif not isinstance(subject, str):
            return
        # --
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


server = SMTPServer()

if __name__ == "__main__":
    print("Running alerts.py as __main__. Please run main.py, instead.")
