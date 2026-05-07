from pico_Reader import RFIDBridge, RFIDBridgeError, rand_Tool_ID
import time

with RFIDBridge("/dev/ttyACM0") as rfid:
    print("Hold card to reader...")
    while True:
        try:
            info = rfid.scan()
            print("UID:", info['uid'])
            tool_id = rfid.read_block(4).rstrip(b'\x00').decode()
            print("Tool ID:", tool_id)
            rfid.write_block(4, 'TBNSE82Z'.encode())
            break
        except RFIDBridgeError as e:
            if "No tag" in str(e):
                time.sleep(0.2)
                continue
            raise
