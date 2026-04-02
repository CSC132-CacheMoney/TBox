import random

import serial
import json
import os

# Load settings
with open(os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')) as f:
    settings = json.load(f)

RFID_CONFIG = settings.get('rfid', {})

def init_rfid(port=None, baud_rate=None):
    """
    Initialize the RFID reader by opening the serial connection.
    
    Args:
        port (str): Serial port (default from settings)
        baud_rate (int): Baud rate (default from settings)
    
    Returns:
        serial.Serial or None: The serial connection object if successful, None otherwise
    """
    port = port or RFID_CONFIG.get('port', '/dev/ttyUSB0')
    baud_rate = baud_rate or RFID_CONFIG.get('baud_rate', 9600)
    
    try:
        reader = serial.Serial(port, baud_rate, timeout=1)
        print(f"RFID reader initialized on {port} at {baud_rate} baud")
        return reader
    except serial.SerialException as e:
        print(f"Failed to initialize RFID reader: {e}")
        return None

def read_rfid_tag(reader):
    """
    Read an RFID tag from the initialized reader.
    
    Args:
        reader (serial.Serial): The initialized RFID reader
    
    Returns:
        str or None: The RFID tag data if read, None if error or no tag
    """
    if not reader or not reader.is_open:
        print("RFID reader not initialized")
        return None
    
    try:
        # Assuming the reader sends data as lines; adjust based on your reader's protocol
        data = reader.readline().decode('utf-8').strip()
        if data:
            print(f"RFID tag read: {data}")
            return data
        return None
    except Exception as e:
        print(f"Error reading RFID tag: {e}")
        return None


def write_rfid_tag(reader):
    tag_data = ("T" + str(random.randint(100000, 999999))) #Generate a random id for the tags ('T' represents it is a tool, not a user)
    """
    Write data to an RFID tag using the reader.
    
    Args:
        reader (serial.Serial): The initialized RFID reader
        tag_data (str): The data to write to the RFID tag
    
    Returns:
        bool: True if write was successful, False otherwise
    """
    
    if not reader or not reader.is_open:
        print("RFID reader not initialized")
        return False
    
    try:
        # Assuming the writer sends data as lines; adjust based on your reader's protocol
        reader.write((tag_data + '\n').encode('utf-8'))
        print(f"RFID tag written: {tag_data}")
        return True
    except Exception as e:
        print(f"Error writing RFID tag: {e}")
        return False
# Example usage:
# reader = init_rfid()
# if reader:
#     tag = read_rfid_tag(reader)
#     if tag:
#         # Use the tag, e.g., register_tool or checkout
#         pass
