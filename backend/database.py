import os
import sqlite3
from datetime import datetime


DB_PATH = "data/tools.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets you access columns by name
    return conn


# ── INITIALIZATION ────────────────────────────────────────────────────────────

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) # Ensure the data directory exists
    """Create all tables if they don't exist. Run once on startup."""
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS tools (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            rfid_tag    TEXT NOT NULL UNIQUE,
            category    TEXT,
            condition   TEXT DEFAULT 'Good',
            status      TEXT DEFAULT 'Available',  -- Available | Checked Out | Retired
            added_on    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS checkouts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id         INTEGER NOT NULL,
            user_name       TEXT NOT NULL,
            checked_out_at  TEXT NOT NULL,
            returned_at     TEXT,           -- NULL means still checked out
            FOREIGN KEY (tool_id) REFERENCES tools(id)
        );

        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            last_seen   TEXT
        );

        CREATE TABLE IF NOT EXISTS config (
            key     TEXT PRIMARY KEY,
            value   TEXT NOT NULL
        );
    """)

    # Insert default config values if they don't exist yet
    c.execute("""
        INSERT OR IGNORE INTO config (key, value) VALUES
            ('checkout_limit_hours', '24'),
            ('alert_method', 'console')
    """)

    conn.commit()
    conn.close()


# ── TOOLS ─────────────────────────────────────────────────────────────────────

def register_tool(name, rfid_tag, category="General", condition="Good"):
    """Add a new tool to the inventory."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO tools (name, rfid_tag, category, condition, status, added_on)
            VALUES (?, ?, ?, ?, 'Available', ?)
        """, (name, rfid_tag, category, condition, datetime.now().isoformat()))
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(f"A tool with RFID tag '{rfid_tag}' already exists.")
    
def get_all_tools():
    """Return a list of all tools in the inventory."""
    conn = get_connection()
    tools = conn.execute("SELECT * FROM tools").fetchall()
    conn.close()
    return tools

def retire_tool(rfid_tag):
    """Mark a tool as retired."""
    conn = get_connection()
    conn.execute("""
        UPDATE tools SET status = 'Retired' WHERE rfid_tag = ?
    """, (rfid_tag,))
    conn.commit()
    conn.close()
    
def checkout_tool(rfid_tag, user_name):
    """Check out a tool to a user."""
    conn = get_connection()
    tool = conn.execute("SELECT * FROM tools WHERE rfid_tag = ?", (rfid_tag,)).fetchone()
    if not tool:
        raise ValueError("Tool not found.")
    if tool["status"] != "Available":
        raise ValueError("Tool is not available for checkout.")
    
    # Mark tool as checked out
    conn.execute("""
        UPDATE tools SET status = 'Checked Out' WHERE rfid_tag = ?
    """, (rfid_tag,))
    
    # Record the checkout
    conn.execute("""
        INSERT INTO checkouts (tool_id, user_name, checked_out_at)
        VALUES (?, ?, ?)
    """, (tool["id"], user_name, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
def return_tool(rfid_tag):
    """Return a checked-out tool."""
    conn = get_connection()
    tool = conn.execute("SELECT * FROM tools WHERE rfid_tag = ?", (rfid_tag,)).fetchone()
    if not tool:
        raise ValueError("Tool not found.")
    if tool["status"] != "Checked Out":
        raise ValueError("Tool is not currently checked out.")
    
    # Mark tool as available
    conn.execute("""
        UPDATE tools SET status = 'Available' WHERE rfid_tag = ?
    """, (rfid_tag,))
    
    # Record the return time for the latest checkout of this tool
    conn.execute("""
        UPDATE checkouts SET returned_at = ?
        WHERE tool_id = ? AND returned_at IS NULL
    """, (datetime.now().isoformat(), tool["id"]))
    
    conn.commit()
    conn.close()
    
def register_user(name):
    """Add a new user or update last seen time if they already exist."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO users (name, last_seen) VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET last_seen = excluded.last_seen
    """, (name, datetime.now().isoformat()))
    conn.commit()
    conn.close()