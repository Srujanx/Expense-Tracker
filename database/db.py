import sqlite3
from datetime import date
from pathlib import Path

from werkzeug.security import generate_password_hash

# Project root = parent of the database/ package dir. Derived from __file__
# so the DB path is correct regardless of the process working directory.
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "expense_tracker.db"

# Fixed category list (spec-mandated; reused by seed + later steps).
CATEGORIES = ["Food", "Transport", "Bills", "Health",
              "Entertainment", "Shopping", "Other"]


def get_db():
    """SQLite connection with Row factory and FK enforcement ON.

    PRAGMA foreign_keys is per-connection and defaults OFF in SQLite, so it
    must be set on every connection — this is the single place that happens.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables. Idempotent via CREATE TABLE IF NOT EXISTS."""
    conn = get_db()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _current_month_date(day):
    """YYYY-MM-DD string for `day` in the current year/month.

    Callers keep `day` <= 28 so it is valid in every month (incl. Feb).
    """
    today = date.today()
    return date(today.year, today.month, day).isoformat()


def seed_db():
    """Insert one demo user + 8 sample expenses, only if users is empty.

    Idempotent: returns early once any user row exists, so re-running on
    startup never duplicates seed data.
    """
    conn = get_db()
    try:
        existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing > 0:
            return

        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com",
             generate_password_hash("demo123")),
        )
        user_id = cur.lastrowid

        # (day, amount, category, description) — all 7 categories, Food twice = 8.
        samples = [
            (2,  12.50, "Food",          "Lunch at cafe"),
            (5,  45.00, "Transport",     "Monthly metro pass top-up"),
            (8,  90.20, "Bills",         "Electricity bill"),
            (11, 30.00, "Health",        "Pharmacy"),
            (15, 25.75, "Entertainment", "Movie tickets"),
            (19, 60.40, "Shopping",      "New running shoes"),
            (23, 18.00, "Other",         "Misc supplies"),
            (27, 22.30, "Food",          "Groceries"),
        ]

        conn.executemany(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(user_id, amount, category, _current_month_date(day), desc)
             for (day, amount, category, desc) in samples],
        )
        conn.commit()
    finally:
        conn.close()
