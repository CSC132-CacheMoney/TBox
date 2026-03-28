import sqlite3
from datetime import datetime

DB_PATH = "data/tools.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets you access columns by name
    return conn


# ── INITIALIZATION ────────────────────────────────────────────────────────────

def init_db():
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
            ('checkout_limit_minutes', '60'),
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