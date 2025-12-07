import os
import sqlite3

# -------------------- CONFIG --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "bookings.db")

# -------------------- SCHEMA --------------------
schema = """
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    bay INTEGER NOT NULL,
    booking_date TEXT NOT NULL,
    slot_start TEXT NOT NULL,
    slot_end TEXT NOT NULL,
    booking_code INTEGER,
    created_at TEXT NOT NULL,
    canceled INTEGER NOT NULL DEFAULT 0,
    tech_remark TEXT DEFAULT '',
    closed INTEGER NOT NULL DEFAULT 0,
    closed_at TEXT
);
"""

# -------------------- HELPER --------------------
def column_exists(cursor, table: str, column: str) -> bool:
    """Check if a column exists in the table."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [c[1] for c in cursor.fetchall()]
    return column in columns

# -------------------- INIT DB --------------------
def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Create table
    cur.executescript(schema)

    # Add missing columns if they don't exist
    extra_columns = [
        ("booking_code", "INTEGER"),
        ("tech_remark", "TEXT DEFAULT ''"),
        ("closed", "INTEGER NOT NULL DEFAULT 0"),
        ("closed_at", "TEXT")
    ]

    for col_name, col_def in extra_columns:
        if not column_exists(cur, "bookings", col_name):
            cur.execute(f"ALTER TABLE bookings ADD COLUMN {col_name} {col_def}")

    # Create indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_phone ON bookings(phone)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_slotbay ON bookings(bay, slot_start)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_booking_code ON bookings(booking_code)")

    conn.commit()
    conn.close()
    print("Database initialized/updated successfully!")

# -------------------- MAIN --------------------
if __name__ == "__main__":
    init_db()
