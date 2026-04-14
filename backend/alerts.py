# alerts.py
# Loki Darius Edullantes Nordstrom
# 
# alerts.py does not actually send emails at the moment. Follow
# the steps below to "receive emails" to the Git Bash console:
# 
# 1.) pip install aiosmtpd or from requirements.txt in Git Bash
# 
# 2.) run main.py as "__main__" to a console
# 
# 3.) run this command in Git Bash:
#     python -m aisomtpd -n -l 127.0.0.1:6767
# 
# 4.) run alerts.py as "__main__" to a second console
# 
# 5.) "Emails" should print to console back in Git Bash
#     thanks to aiosmtpd.
# 
# ------------------------------------------------


from smtplib import SMTP
from time import sleep
import aiosmtpd as server
from email.mime.text import MIMEText
from subprocess import *

# ------------------------------------------------


HOST = "127.0.0.1"
PORT = 6969
ADDRESS_FROM = f"http://{HOST}:{PORT}"
ADDRESS_TO = "len016@email.latech.edu"


# ------------------------------------------------


# Alert class
class SMTPConsole:
    # Constructor
    def __init__(self):
        self.start(
            HOST,
            PORT
        )
        # self.smtp.ehlo()
        # self.smtp.starttls()
    
    
    # String
    def __str__(self):
        return "Alert object"
    
    
    # Alert.smtp
    @property
    def smtp(self):
        return self._smtp
    # --
    @smtp.setter
    def smtp(self, smtp):
        if not isinstance(smtp, SMTP):
            raise Exception(f"Alert.smtp -> attempted to assign non-SMTP: {smtp}")
        self._smtp = smtp
    
    
    # Alert methods
    def start(self, host: str, port: int):
        if not isinstance(host, str) or not isinstance(port, int):
            return
        self.smtp = SMTP(
            host,
            port,
            timeout = 30.0
        ) 
    # --
    def registered(self):
        self.smtp.sendmail(
            ADDRESS_FROM,
            ADDRESS_TO,
            "An item has been registered to ToolVault."
        )
    # --
    def checked_out(self):
        self.smtp.sendmail(
            ADDRESS_FROM,
            ADDRESS_TO,
            "An item has been checked-out from ToolVault."
        )
    # --
    def checked_in(self):
        self.smtp.sendmail(
            ADDRESS_FROM,
            ADDRESS_TO,
            "An item has been check-in into ToolVault."
        )
    # --
    def retired(self):
        self.smtp.sendmail(
            ADDRESS_FROM,
            ADDRESS_TO,
            "An item has been retired from ToolVault."
        )
    # --
    def quit(self):
        self.smtp.quit()

"""
# Alert class
class SMTPServer:
    # Constructor
    def __init__(self):
        self.smtp = SMTP(
            "smtp.gmail.com",
            587
        )
        self.smtp.starttls()
        self.smtp.login("len016@email.latech.edu")
    
    
    # SMTPServer methods
    def send_message(self, subject = "Subject", text = "Text."):
        message = MIMEText(text)
        message["Subject"] = subject
        message["From"] = ""
        self.smtp.send_message()
"""

def initalerts():
    print("Initializing alerts system...")
    try:
        command = "python -m aiosmtpd -n -l 127.0.0.1:6969"
        run(command, shell=True, check=True)
        print("SMTP server started successfully.")
    except Exception as e:
        print(f"Error starting SMTP server: {e}")
        
def test_alerts():
    alert = SMTPConsole()
    sleep(3)
    alert.registered()
    sleep(3)
    alert.checked_in()
    sleep(3)
    alert.checked_out()
    sleep(3)
    alert.retired()

# ------------------------------------------------


if __name__ == "__main__":
    alert = SMTPConsole()
    sleep(3)
    alert.registered()
    sleep(3)
    alert.checked_in()
    sleep(3)
    alert.checked_out()
    sleep(3)
    alert.retired()
