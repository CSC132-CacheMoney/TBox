import os
import sqlite3
from datetime import datetime
from pathlib import Path
import pico_Reader

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "tools.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets you access columns by name
    return conn


# ── INITIALIZATION ────────────────────────────────────────────────────────────

def init_db():
    os.makedirs(DB_PATH.parent, exist_ok=True)  # Ensure the data directory exists
    """Create all tables if they don't exist. Run once on startup."""
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS tools (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            brand       TEXT DEFAULT '',
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

    # Migrate existing databases: add brand column if absent
    try:
        c.execute("ALTER TABLE tools ADD COLUMN brand TEXT DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists

    conn.close()


# ── TOOLS ─────────────────────────────────────────────────────────────────────

def display_name(tool) -> str:
    """Return 'Name (Brand)' if brand is set, otherwise just 'Name'."""
    brand = (tool.get("brand") or "").strip()
    return f"{tool['name']} ({brand})" if brand else tool["name"]


def register_tool(name, rfid_tag=pico_Reader.rand_Tool_ID(), category="General", condition="Good", brand=""):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO tools (name, brand, rfid_tag, category, condition, status, added_on)
            VALUES (?, ?, ?, ?, ?, 'Available', ?)
        """, (name, brand.strip(), rfid_tag, category, condition, datetime.now().isoformat()))
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError(f"A tool with RFID tag '{rfid_tag}' already exists.")
    finally:
        conn.close()
 
 
def retire_tool(tool_id):
    conn = get_connection()
    conn.execute("UPDATE tools SET status = 'Retired' WHERE id = ?", (tool_id,))
    conn.commit()
    conn.close()
 
 
def get_all_tools():
    conn = get_connection()
    tools = conn.execute("SELECT * FROM tools ORDER BY name").fetchall()
    conn.close()
    return tools
 
 
def get_tool_by_id(tool_id):
    conn = get_connection()
    tool = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
    conn.close()
    return tool

def valid_tool_id(tool_id):
    conn = get_connection()
    try:
        get_tool_by_rfid(tool_id)
        return True
    except:
        return False
    finally:
        conn.close
 
def get_tool_by_rfid(rfid_tag):
    conn = get_connection()
    tool = conn.execute("SELECT * FROM tools WHERE rfid_tag = ?", (rfid_tag,)).fetchone()
    conn.close()
    return tool
 
 
def get_active_tools():
    """All tools that are not retired."""
    conn = get_connection()
    tools = conn.execute(
        "SELECT * FROM tools WHERE status != 'Retired' ORDER BY name"
    ).fetchall()
    conn.close()
    return tools
 
 
# ── CHECKOUTS ─────────────────────────────────────────────────────────────────
 
def checkout_tool(tool_id, user_name):
    conn = get_connection()
    tool = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
 
    if not tool:
        conn.close()
        raise ValueError("Tool not found.")
    if tool["status"] != "Available":
        conn.close()
        raise ValueError(f"'{tool['name']}' is not available (status: {tool['status']}).")
 
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO checkouts (tool_id, user_name, checked_out_at) VALUES (?, ?, ?)",
        (tool_id, user_name, now)
    )
    conn.execute("UPDATE tools SET status = 'Checked Out' WHERE id = ?", (tool_id,))
    conn.commit()
    conn.close()
 
 
def return_tool(tool_id):
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE checkouts SET returned_at = ? WHERE tool_id = ? AND returned_at IS NULL",
        (now, tool_id)
    )
    conn.execute("UPDATE tools SET status = 'Available' WHERE id = ?", (tool_id,))
    conn.commit()
    conn.close()
 
 
def get_overdue_checkouts():
    limit = int(get_config("checkout_limit_minutes"))
    conn = get_connection()
    open_checkouts = conn.execute("""
        SELECT checkouts.*, tools.name AS tool_name, tools.rfid_tag
        FROM checkouts
        JOIN tools ON checkouts.tool_id = tools.id
        WHERE checkouts.returned_at IS NULL
    """).fetchall()
    conn.close()
 
    overdue = []
    now = datetime.now()
    for row in open_checkouts:
        checked_out_at = datetime.fromisoformat(row["checked_out_at"])
        minutes_out = (now - checked_out_at).total_seconds() / 60
        if minutes_out > limit:
            overdue.append({
                "tool_name":       row["tool_name"],
                "rfid_tag":        row["rfid_tag"],
                "user_name":       row["user_name"],
                "checked_out_at":  row["checked_out_at"],
                "minutes_overdue": round(minutes_out - limit)
            })
    return overdue
 
 
def get_checkout_history(tool_id):
    conn = get_connection()
    history = conn.execute(
        "SELECT * FROM checkouts WHERE tool_id = ? ORDER BY checked_out_at DESC",
        (tool_id,)
    ).fetchall()
    conn.close()
    return history
 
 
# ── USERS ─────────────────────────────────────────────────────────────────────
 
def log_user(name):
    conn = get_connection()
    conn.execute("""
        INSERT INTO users (name, last_seen) VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET last_seen = excluded.last_seen
    """, (name, datetime.now().isoformat()))
    conn.commit()
    conn.close()
 
 
# ── CONFIG ────────────────────────────────────────────────────────────────────
 
def get_config(key):
    conn = get_connection()
    row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None
 
 
def set_config(key, value):
    conn = get_connection()
    conn.execute("""
        INSERT INTO config (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, str(value)))
    conn.commit()
    conn.close()
 
 
# ── DASHBOARD ─────────────────────────────────────────────────────────────────

def get_dashboard_stats():
    conn = get_connection()
    row = conn.execute("""
        SELECT
            SUM(CASE WHEN status = 'Available'   THEN 1 ELSE 0 END) AS available,
            SUM(CASE WHEN status = 'Checked Out' THEN 1 ELSE 0 END) AS checked_out,
            SUM(CASE WHEN status = 'Retired'     THEN 1 ELSE 0 END) AS retired,
            SUM(CASE WHEN status != 'Retired'    THEN 1 ELSE 0 END) AS active
        FROM tools
    """).fetchone()
    conn.close()
    return {k: (row[k] or 0) for k in row.keys()}


def get_longest_checkout():
    conn = get_connection()
    row = conn.execute("""
        SELECT c.user_name,
               CASE WHEN t.brand != '' AND t.brand IS NOT NULL
                    THEN t.name || ' (' || t.brand || ')'
                    ELSE t.name END AS tool_name,
               c.checked_out_at
        FROM checkouts c
        JOIN tools t ON c.tool_id = t.id
        WHERE c.returned_at IS NULL
        ORDER BY c.checked_out_at ASC
        LIMIT 1
    """).fetchone()
    conn.close()
    return dict(row) if row else None


def get_weekly_checkouts():
    from datetime import date, timedelta
    conn = get_connection()
    rows = conn.execute("""
        SELECT DATE(checked_out_at) AS day, COUNT(*) AS count
        FROM checkouts
        WHERE DATE(checked_out_at) >= DATE('now', '-6 days')
        GROUP BY DATE(checked_out_at)
    """).fetchall()
    conn.close()
    day_map = {r["day"]: r["count"] for r in rows}
    today = date.today()
    return [
        {"day": (today - timedelta(days=i)).isoformat(),
         "count": day_map.get((today - timedelta(days=i)).isoformat(), 0)}
        for i in range(6, -1, -1)
    ]


def get_recent_activity(since=None, limit=25):
    conn = get_connection()
    if since:
        rows = conn.execute("""
            SELECT 'checkout' AS type, c.user_name,
                   CASE WHEN t.brand != '' AND t.brand IS NOT NULL
                        THEN t.name || ' (' || t.brand || ')' ELSE t.name END AS tool_name,
                   c.checked_out_at AS event_time
            FROM checkouts c JOIN tools t ON c.tool_id = t.id
            WHERE c.checked_out_at > ?

            UNION ALL

            SELECT 'return' AS type, c.user_name,
                   CASE WHEN t.brand != '' AND t.brand IS NOT NULL
                        THEN t.name || ' (' || t.brand || ')' ELSE t.name END AS tool_name,
                   c.returned_at AS event_time
            FROM checkouts c JOIN tools t ON c.tool_id = t.id
            WHERE c.returned_at IS NOT NULL AND c.returned_at > ?

            UNION ALL

            SELECT 'login' AS type, u.name AS user_name, NULL AS tool_name,
                   u.last_seen AS event_time
            FROM users u WHERE u.last_seen > ?

            ORDER BY event_time DESC LIMIT ?
        """, (since, since, since, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT 'checkout' AS type, c.user_name,
                   CASE WHEN t.brand != '' AND t.brand IS NOT NULL
                        THEN t.name || ' (' || t.brand || ')' ELSE t.name END AS tool_name,
                   c.checked_out_at AS event_time
            FROM checkouts c JOIN tools t ON c.tool_id = t.id

            UNION ALL

            SELECT 'return' AS type, c.user_name,
                   CASE WHEN t.brand != '' AND t.brand IS NOT NULL
                        THEN t.name || ' (' || t.brand || ')' ELSE t.name END AS tool_name,
                   c.returned_at AS event_time
            FROM checkouts c JOIN tools t ON c.tool_id = t.id
            WHERE c.returned_at IS NOT NULL

            UNION ALL

            SELECT 'login' AS type, u.name AS user_name, NULL AS tool_name,
                   u.last_seen AS event_time
            FROM users u WHERE u.last_seen IS NOT NULL

            ORDER BY event_time DESC LIMIT ?
        """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print("Database initialized.")