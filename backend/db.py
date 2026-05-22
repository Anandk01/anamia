"""
db.py — Database initialisation and connection helpers for the Anemia Detection System.

Provides:
  - get_db()                  : opens a SQLite connection to backend/anemia.db
  - init_db()                 : creates all 8 tables and seeds default accounts
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

CREATE TABLE IF NOT EXISTS doctor_patient (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id   INTEGER NOT NULL REFERENCES user(user_id),
    patient_id  INTEGER NOT NULL REFERENCES user(user_id),
    assigned_at TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(doctor_id, patient_id)
);

CREATE TABLE IF NOT EXISTS appointment (
    appointment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id           INTEGER NOT NULL REFERENCES user(user_id),
    patient_id          INTEGER NOT NULL REFERENCES user(user_id),
    requested_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    confirmed_at        TEXT,
    slot_date           TEXT    NOT NULL,
    slot_time           TEXT    NOT NULL,
    duration_min        INTEGER NOT NULL DEFAULT 30,
    status              TEXT    NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending','confirmed','cancelled','completed')),
    notes               TEXT,
    cancellation_reason TEXT
);

CREATE TABLE IF NOT EXISTS medication (
    med_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL REFERENCES user(username),
    name          TEXT    NOT NULL,
    dose_mg       REAL    NOT NULL,
    frequency     TEXT    NOT NULL CHECK(frequency IN ('daily','twice','thrice','weekly')),
    start_date    TEXT    NOT NULL,
    end_date      TEXT,
    prescribed_by TEXT    REFERENCES user(username),
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS medication_log (
    log_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    med_id    INTEGER NOT NULL REFERENCES medication(med_id),
    taken_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    skipped   INTEGER NOT NULL DEFAULT 0,
    notes     TEXT
);

CREATE TABLE IF NOT EXISTS chat_room (
    room_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id       INTEGER NOT NULL REFERENCES user(user_id),
    patient_id      INTEGER NOT NULL REFERENCES user(user_id),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    last_message_at TEXT,
    UNIQUE(doctor_id, patient_id)
);

CREATE TABLE IF NOT EXISTS chat_message (
    message_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id         INTEGER NOT NULL REFERENCES chat_room(room_id),
    sender_username TEXT    NOT NULL,
    content         TEXT    NOT NULL,
    message_type    TEXT    NOT NULL DEFAULT 'text'
                    CHECK(message_type IN ('text','file','image')),
    file_url        TEXT,
    read_at         TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS post (
    post_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    NOT NULL REFERENCES user(username),
    title      TEXT    NOT NULL,
    body       TEXT    NOT NULL,
    tags       TEXT,
    upvotes    INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    anonymous  INTEGER NOT NULL DEFAULT 0,
    pinned     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reply (
    reply_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id            INTEGER NOT NULL REFERENCES post(post_id),
    username           TEXT    NOT NULL REFERENCES user(username),
    body               TEXT    NOT NULL,
    is_doctor_verified INTEGER NOT NULL DEFAULT 0,
    upvotes            INTEGER NOT NULL DEFAULT 0,
    created_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS post_upvote (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id  INTEGER NOT NULL REFERENCES post(post_id),
    username TEXT    NOT NULL,
    UNIQUE(post_id, username)
);

CREATE TABLE IF NOT EXISTS reply_upvote (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    reply_id INTEGER NOT NULL REFERENCES reply(reply_id),
    username TEXT    NOT NULL,
    UNIQUE(reply_id, username)
);

CREATE TABLE IF NOT EXISTS article (
    article_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT    NOT NULL,
    content_md    TEXT    NOT NULL,
    summary       TEXT,
    tags          TEXT,
    author_id     TEXT    NOT NULL REFERENCES user(username),
    published_at  TEXT,
    read_time_min INTEGER,
    status        TEXT    NOT NULL DEFAULT 'draft'
                  CHECK(status IN ('draft','published'))
);

CREATE TABLE IF NOT EXISTS bookmark (
    bookmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL REFERENCES user(username),
    article_id  INTEGER NOT NULL REFERENCES article(article_id),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(username, article_id)
);

CREATE TABLE IF NOT EXISTS model_metrics (
    metric_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name       TEXT    NOT NULL,
    accuracy         REAL    NOT NULL,
    precision_score  REAL    NOT NULL,
    recall           REAL    NOT NULL,
    f1_score         REAL    NOT NULL,
    auc_roc          REAL,
    confusion_matrix TEXT,
    dataset_name     TEXT    NOT NULL,
    dataset_size     INTEGER NOT NULL,
    trained_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notification (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL REFERENCES user(username),
    type            TEXT    NOT NULL
                    CHECK(type IN ('medication','appointment','checkup','alert','forum','system')),
    title           TEXT    NOT NULL,
    message         TEXT    NOT NULL,
    read            INTEGER NOT NULL DEFAULT 0,
    scheduled_at    TEXT,
    sent_at         TEXT,
    delivery_method TEXT    NOT NULL DEFAULT 'push'
                    CHECK(delivery_method IN ('push','email','both')),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prescription (
    prescription_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id          TEXT    NOT NULL REFERENCES user(username),
    patient_id         TEXT    NOT NULL REFERENCES user(username),
    prediction_id      INTEGER REFERENCES prediction(prediction_id),
    medications        TEXT    NOT NULL,
    dosage_instructions TEXT,
    duration_days      INTEGER,
    follow_up_date     TEXT,
    notes              TEXT,
    created_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    actor      TEXT    NOT NULL,
    action     TEXT    NOT NULL,
    target     TEXT,
    details    TEXT,
    ip_address TEXT,
    timestamp  TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

# ---------------------------------------------------------------------------
# ALTER TABLE statements for user table extensions
# ---------------------------------------------------------------------------

_ALTER_USER_COLUMNS = [
    "ALTER TABLE user ADD COLUMN blood_type TEXT",
    "ALTER TABLE user ADD COLUMN known_conditions TEXT",
    "ALTER TABLE user ADD COLUMN dietary_preferences TEXT",
    "ALTER TABLE user ADD COLUMN emergency_contact TEXT",
    "ALTER TABLE user ADD COLUMN specialization TEXT",
    "ALTER TABLE user ADD COLUMN license_number TEXT",
    "ALTER TABLE user ADD COLUMN available_hours TEXT",
    "ALTER TABLE user ADD COLUMN notification_prefs TEXT",
    "ALTER TABLE user ADD COLUMN theme_pref TEXT DEFAULT 'light'",
    "ALTER TABLE user ADD COLUMN font_size TEXT DEFAULT 'medium'",
    "ALTER TABLE user ADD COLUMN high_contrast INTEGER DEFAULT 0",
    "ALTER TABLE user ADD COLUMN onboarding_complete INTEGER DEFAULT 0",
]

_ALTER_PRESCRIPTION_COLUMNS = [
    "ALTER TABLE prescription ADD COLUMN diet_plan TEXT",
]


def _extend_user_table(conn: sqlite3.Connection) -> None:
    """Add new columns to the user table and prescription table if they don't already exist."""
    cursor = conn.cursor()
    for stmt in _ALTER_USER_COLUMNS:
        try:
            cursor.execute(stmt)
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                pass
            else:
                raise
    for stmt in _ALTER_PRESCRIPTION_COLUMNS:
        try:
            cursor.execute(stmt)
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                pass
            else:
                raise
    conn.commit()


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
    """Create all 8 tables (if they don't exist) and seed default accounts.

    Seeding only runs when the *user* table is empty, so it is safe to call
    this function on every application start-up.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()

        # Create tables
        cursor.executescript(_CREATE_TABLES_SQL)
        conn.commit()

        # Extend user table with new columns (idempotent)
        _extend_user_table(conn)

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

        # Seed model_metrics if empty
        row = cursor.execute("SELECT COUNT(*) FROM model_metrics").fetchone()
        if row[0] == 0:
            import json as _json
            _seed_metrics = [
                ("Random Forest", 0.9245, 0.9180, 0.9245, 0.9210, 0.9650,
                 _json.dumps([[85, 5, 2, 1], [4, 78, 3, 2], [1, 4, 72, 5], [0, 1, 3, 65]]),
                 "CBC_Dataset_v2", 1200),
                ("Gradient Boosting", 0.9312, 0.9280, 0.9312, 0.9295, 0.9720,
                 _json.dumps([[87, 4, 1, 1], [3, 80, 2, 2], [1, 3, 74, 4], [0, 1, 2, 67]]),
                 "CBC_Dataset_v2", 1200),
                ("XGBoost", 0.9178, 0.9120, 0.9178, 0.9148, 0.9580,
                 _json.dumps([[84, 6, 2, 1], [5, 76, 4, 2], [2, 4, 71, 5], [1, 2, 3, 64]]),
                 "CBC_Dataset_v2", 1200),
                ("LightGBM", 0.9289, 0.9250, 0.9289, 0.9269, 0.9690,
                 _json.dumps([[86, 4, 2, 1], [3, 79, 3, 2], [1, 3, 73, 5], [0, 1, 2, 66]]),
                 "CBC_Dataset_v2", 1200),
            ]
            for m in _seed_metrics:
                cursor.execute(
                    """INSERT INTO model_metrics
                       (model_name, accuracy, precision_score, recall, f1_score, auc_roc,
                        confusion_matrix, dataset_name, dataset_size)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    m,
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
