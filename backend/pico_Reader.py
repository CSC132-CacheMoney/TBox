import random
import string


def read_rfid_tag():
    """Simulate reading an RFID tag by prompting the user for input."""
    pass

def rand_Tool_ID():
    """Generate a random 8-character alphanumeric string."""
    return 'T' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))

def write_rfid_tag(tool_id):
    """Simulate writing an RFID tag by printing the tool ID."""
    print(f"Writing RFID tag for tool ID: {tool_id}")