


"""
rfid_host.py  –  Host-side Python library + CLI for the Pico RFID bridge
Requires:  pip install pyserial

Usage (CLI):
    python rfid_host.py --port COM3 scan
    python rfid_host.py --port /dev/ttyACM0 read  --block 4
    python rfid_host.py --port /dev/ttyACM0 write --block 4 --data "Hello, RFID!!!!!"
    python rfid_host.py --port /dev/ttyACM0 ping

Usage (library):
    from rfid_host import RFIDBridge

    with RFIDBridge("COM3") as rfid:
        uid_info = rfid.scan()
        print(uid_info)

        data = rfid.read_block(4)
        print(data)

        rfid.write_block(4, b"Hello, RFID!!!!!")
"""

import json
import time
import argparse
import serial          # pip install pyserial
from typing import Optional
import random
import string



def rand_Tool_ID():
    """Generate a random 8-character alphanumeric string."""
    return 'T' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))



# ── Configuration ──────────────────────────────────────────────────────────────
DEFAULT_BAUD    = 115200
DEFAULT_TIMEOUT = 3.0   # seconds to wait for a response
# ──────────────────────────────────────────────────────────────────────────────


class RFIDBridgeError(Exception):
    pass


class RFIDBridge:
    """
    Serial bridge to the Pico RFID firmware.

    Parameters
    ----------
    port    : serial port string, e.g. 'COM3' or '/dev/ttyACM0'
    baud    : baud rate (must match firmware; default 115200)
    timeout : read timeout in seconds
    """

    def __init__(self, port: str, baud: int = DEFAULT_BAUD,
                 timeout: float = DEFAULT_TIMEOUT):
        self.port    = port
        self.baud    = baud
        self.timeout = timeout
        self._ser: Optional[serial.Serial] = None

    # ── Context manager ───────────────────────────────────────────────────────
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()

    # ── Connection management ─────────────────────────────────────────────────
    def open(self):
        """Open the serial port and verify the Pico is responsive."""
        self._ser = serial.Serial(
            self.port, self.baud, timeout=self.timeout,
            dsrdtr=False, rtscts=False
        )
        self._ser.dtr = False
        time.sleep(0.1)
        self._ser.reset_input_buffer()

        # Fast path: Pico already running main.py, just ping it
        try:
            r = self._send({"cmd": "ping"})
            if r.get("status") == "ok":
                return
        except RFIDBridgeError:
            pass

        # Slow path: Pico just booted, wait for the ready message
        deadline = time.time() + 5.0
        while time.time() < deadline:
            line = self._ser.readline().decode(errors="replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                if msg.get("status") == "ready":
                    return
            except json.JSONDecodeError:
                pass
        raise RFIDBridgeError("Pico did not respond within 5 seconds")


    def close(self):
        if self._ser and self._ser.is_open:
            self._ser.close()

    # ── Low-level send/receive ────────────────────────────────────────────────
    def _send(self, obj: dict) -> dict:
        """Send a JSON command and return the parsed JSON response."""
        if self._ser is None or not self._ser.is_open:
            raise RFIDBridgeError("Serial port is not open")
        payload = (json.dumps(obj) + "\n").encode()
        self._ser.write(payload)
        self._ser.flush()

        deadline = time.time() + self.timeout
        while time.time() < deadline:
            raw = self._ser.readline().decode(errors="replace").strip()
            if not raw:
                continue
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                continue
        raise RFIDBridgeError("Timeout waiting for response from Pico")

    def _require_ok(self, response: dict) -> dict:
        if response.get("status") == "ok":
            return response
        if response.get("status") == "no_tag":
            raise RFIDBridgeError("No tag present")
        raise RFIDBridgeError(response.get("msg", "Unknown error from firmware"))

    # ── Public API ────────────────────────────────────────────────────────────
    def ping(self) -> bool:
        """Returns True if the Pico responds to a ping."""
        r = self._send({"cmd": "ping"})
        return r.get("status") == "ok"

    def scan(self) -> dict:
        """
        Scan for a tag. Returns a dict with keys:
            uid  – list of UID bytes
            sak  – Select Acknowledge byte (int)
        """
        r = self._require_ok(self._send({"cmd": "scan"}))
        return {"uid": r["uid"], "sak": r["sak"]}

    def read_block(self, block: int,
                   key: Optional[list] = None) -> bytes:
        """
        Read 16 bytes from *block* (0-6 self._require_ok(3 for MIFARE Classic 1K).
        *key* is an optional list of 6 ints (Key A). Defaults to FF FF FF FF FF FF.
        Returns bytes of length 16.
        """
        cmd = {"cmd": "read", "block": block}
        if key is not None:
            cmd["key"] = key
        r = self._require_ok(self._send(cmd))
        return bytes(r["data"])

    def write_block(self, block: int, data = rand_Tool_ID(),
                    key: Optional[list] = None) -> None:
        """
        Write exactly 16 bytes to *block*.
        *data* may be bytes, bytearray, list of ints, or a str (padded/truncated to 16).
        *key* is an optional list of 6 ints (Key A). Defaults to FF FF FF FF FF FF.
        """
        if isinstance(data, str):
            encoded = data.encode()[:16]
            encoded = encoded.ljust(16, b"\x00")
        else:
            encoded = bytes(data)[:16]
            encoded = encoded.ljust(16, b"\x00")

        if len(encoded) != 16:
            raise ValueError("data must be exactly 16 bytes")

        cmd = {"cmd": "write", "block": block, "data": list(encoded)}
        if key is not None:
            cmd["key"] = key
        self._require_ok(self._send(cmd))

    def read_all_data_blocks(self, key: Optional[list] = None,
                             num_sectors: int = 16) -> dict:
        """
        Read all user-accessible data blocks (skip sector trailers).
        Returns a dict mapping block_number -> bytes.
        Works for MIFARE Classic 1K (16 sectors x 4 blocks, blocks 0-63).
        """
        results = {}
        for sector in range(num_sectors):
            for b in range(3):   # blocks 0-2 are data; block 3 is trailer
                block_num = sector * 4 + b
                if block_num == 0:
                    continue     # manufacturer block – skip
                try:
                    data = self.read_block(block_num, key)
                    results[block_num] = data
                except RFIDBridgeError:
                    results[block_num] = None
        return results


# ── CLI ────────────────────────────────────────────────────────────────────────

def _fmt_uid(uid_list):
    return ":".join(f"{b:02X}" for b in uid_list)

def _fmt_bytes(raw: Optional[bytes]):
    if raw is None:
        return "(error)"
    hex_str  = " ".join(f"{b:02X}" for b in raw)
    printable = "".join(chr(b) if 32 <= b < 127 else "." for b in raw)
    return f"{hex_str}  |{printable}|"


def main():
    parser = argparse.ArgumentParser(
        description="Host CLI for the Pico RFID USB bridge"
    )
    parser.add_argument("--port",    required=True, help="Serial port, e.g. COM3 or /dev/ttyACM0")
    parser.add_argument("--baud",    type=int, default=DEFAULT_BAUD, help="Baud rate (default 115200)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Response timeout in seconds")
    parser.add_argument("--key",     type=str, default=None,
                        help="Auth key A as 6 hex bytes separated by colons, e.g. FF:FF:FF:FF:FF:FF")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ping",  help="Check connectivity")
    sub.add_parser("scan",  help="Scan for a tag and return its UID")

    p_read = sub.add_parser("read", help="Read a block from a tag")
    p_read.add_argument("--block", type=int, required=True, help="Block number (0-63)")

    p_write = sub.add_parser("write", help="Write a block to a tag")
    p_write.add_argument("--block", type=int, required=True, help="Block number (1-62, avoid 0 & trailers)")
    p_write.add_argument("--data",  type=str, required=True,
                         help="16-byte payload as a quoted string or hex bytes (AA:BB:...)")

    p_dump = sub.add_parser("dump", help="Dump all readable blocks from a tag")
    p_dump.add_argument("--sectors", type=int, default=16, help="Number of sectors to read (default 16 = 1K card)")

    args = parser.parse_args()

    key = None
    if args.key:
        key = [int(x, 16) for x in args.key.split(":")]
        if len(key) != 6:
            parser.error("--key must contain exactly 6 hex bytes")

    try:
        with RFIDBridge(args.port, args.baud, args.timeout) as rfid:

            if args.command == "ping":
                ok = rfid.ping()
                print("PONG – Pico is alive" if ok else "No response")

            elif args.command == "scan":
                info = rfid.scan()
                print(f"UID : {_fmt_uid(info['uid'])}")
                print(f"SAK : 0x{info['sak']:02X}")

            elif args.command == "read":
                data = rfid.read_block(args.block, key)
                print(f"Block {args.block:2d}: {_fmt_bytes(data)}")

            elif args.command == "write":
                raw = args.data
                # Detect hex format AA:BB:CC...
                if ":" in raw and len(raw.replace(":", "")) == 32:
                    payload = bytes(int(x, 16) for x in raw.split(":"))
                else:
                    payload = raw.encode()[:16].ljust(16, b"\x00")
                rfid.write_block(args.block, payload, key)
                print(f"Block {args.block} written successfully.")

            elif args.command == "dump":
                print("Reading tag…  (present tag and keep still)")
                blocks = rfid.read_all_data_blocks(key, args.sectors)
                print(f"\n{'Block':>5}  {'Hex':47}  ASCII")
                print("-" * 70)
                for blk, data in sorted(blocks.items()):
                    print(f"  {blk:3d}:  {_fmt_bytes(data)}")

    except RFIDBridgeError as e:
        print(f"[ERROR] {e}")
    except serial.SerialException as e:
        print(f"[SERIAL ERROR] {e}")

#------GLOBAL FUNCTIONS-------

def init_rfid_hardware():
    """
        Initializes the rfid reader when needed. Still need to call
        scan() after this function.
        """
    global global_reader
    for port in ["/dev/ttyACM0", "/dev/ttyACM1"]:
        try:
            print(f"[STARTUP] Attempting to initialize RFID on {port}...")
            global_reader = RFIDBridge(port)
            global_reader.open()
            print(f"[STARTUP] RFID Reader ready on {port}")
            return
        except Exception as e:
            print(f"[STARTUP] Could not open {port}: {e}")
    print("[STARTUP] WARNING: No RFID reader found.")
    
if __name__ == "__main__":
    main()

