"""
db.py — Database initialisation and connection helpers for the Anemia Detection System.

Provides:
  - get_db()                  : opens a SQLite connection to backend/anemia.db
  - init_db()                 : creates all 6 tables and seeds default accounts
  - log_access_violation(...) : inserts a row into access_violation_log
"""

import os
import sqlite3
from datetime import datetime

import bcrypt

# Absolute path to the SQLite database file, co-located with this module.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anemia.db")


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    """Open and return a SQLite connection with row_factory set to sqlite3.Row.

    The caller is responsible for closing the connection (or using it as a
    context manager).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS user (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL UNIQUE,
    email           TEXT    NOT NULL UNIQUE,
    password_hash   TEXT    NOT NULL,
    role            TEXT    NOT NULL DEFAULT 'patient',
    status          TEXT    NOT NULL DEFAULT 'active',
    language_pref   TEXT    NOT NULL DEFAULT 'en',
    vegan_diet      INTEGER NOT NULL DEFAULT 0,
    age             INTEGER,
    sex             INTEGER,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prediction (
    prediction_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL,
    rbc             REAL    NOT NULL,
    mcv             REAL    NOT NULL,
    mch             REAL    NOT NULL,
    mchc            REAL    NOT NULL,
    rdw             REAL    NOT NULL,
    tlc             REAL    NOT NULL,
    plt             REAL    NOT NULL,
    hgb             REAL    NOT NULL,
    anemia_detected INTEGER NOT NULL,
    severity_level  TEXT    NOT NULL,
    anemia_type     TEXT    NOT NULL,
    confidence      REAL,
    explanation     TEXT,
    diet_recs       TEXT,
    health_tips     TEXT,
    risk_category   TEXT    NOT NULL DEFAULT 'N/A',
    date            TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS alert_log (
    alert_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id      INTEGER NOT NULL,
    recipient_email    TEXT    NOT NULL,
    recipient_username TEXT    NOT NULL,
    patient_username   TEXT    NOT NULL,
    hgb_value          REAL    NOT NULL,
    severity_level     TEXT    NOT NULL,
    sent_at            TEXT    NOT NULL,
    delivery_status    TEXT    NOT NULL DEFAULT 'pending',
    retry_count        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS jwt_blacklist (
    jti TEXT PRIMARY KEY,
    exp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS access_violation_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL,
    endpoint    TEXT    NOT NULL,
    role_claim  TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL,
    ip_address  TEXT,
    action      TEXT
);

CREATE TABLE IF NOT EXISTS retrain_log (
    retrain_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_username  TEXT    NOT NULL,
    dataset_size    INTEGER NOT NULL,
    accuracy        REAL,
    precision_score REAL,
    recall          REAL,
    f1_score        REAL,
    status          TEXT    NOT NULL,
    triggered_at    TEXT    NOT NULL,
    completed_at    TEXT
);
"""

# ---------------------------------------------------------------------------
# Default seed accounts
# ---------------------------------------------------------------------------

_SEED_ACCOUNTS = [
    {
        "username": "admin",
        "email": "admin@anemia.local",
        "password": "Admin@123",
        "role": "admin",
    },
    {
        "username": "doctor",
        "email": "doctor@anemia.local",
        "password": "Doctor@123",
        "role": "doctor",
    },
]


def _hash_password(plain: str) -> str:
    """Return a bcrypt hash (cost=12) of *plain* as a UTF-8 string."""
    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all 6 tables (if they don't exist) and seed default accounts.

    Seeding only runs when the *user* table is empty, so it is safe to call
    this function on every application start-up.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()

        # Create tables
        cursor.executescript(_CREATE_TABLES_SQL)
        conn.commit()

        # Seed default accounts only when the user table is empty
        row = cursor.execute("SELECT COUNT(*) FROM user").fetchone()
        if row[0] == 0:
            for account in _SEED_ACCOUNTS:
                password_hash = _hash_password(account["password"])
                cursor.execute(
                    """
                    INSERT INTO user (username, email, password_hash, role, status)
                    VALUES (?, ?, ?, ?, 'active')
                    """,
                    (account["username"], account["email"], password_hash, account["role"]),
                )
            conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Audit helper
# ---------------------------------------------------------------------------

def log_access_violation(
    username: str,
    endpoint: str,
    role_claim: str,
    ip_address: str | None = None,
    action: str | None = None,
) -> None:
    """Insert a row into *access_violation_log*.

    Parameters
    ----------
    username:   The username of the requester (from JWT or 'anonymous').
    endpoint:   The Flask endpoint / URL path that was accessed.
    role_claim: The role value present in the JWT at the time of the request.
    ip_address: Optional remote IP address of the requester.
    action:     Optional free-text description of the attempted action.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO access_violation_log
                (username, endpoint, role_claim, timestamp, ip_address, action)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, endpoint, role_claim, timestamp, ip_address, action),
        )
        conn.commit()
    finally:
        conn.close()
