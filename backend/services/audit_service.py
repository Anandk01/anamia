"""
audit_service.py — Audit logging service for the AnemiaCare system.

Provides:
  - log_action(actor, action, target, details, ip) : inserts a row into audit_log
  - get_audit_logs(page, per_page, actor, action)  : paginated audit log retrieval
"""

import json
from datetime import datetime, timezone

from db import get_db


def log_action(
    actor: str,
    action: str,
    target: str | None = None,
    details: dict | None = None,
    ip: str | None = None,
) -> int:
    """Insert a row into the audit_log table.

    Parameters
    ----------
    actor : str
        Username or identifier of the person performing the action.
    action : str
        Short description of the action (e.g. "login_success", "user_create").
    target : str | None
        The entity being acted upon (e.g. a username, resource id).
    details : dict | None
        Additional context serialized as JSON.
    ip : str | None
        IP address of the requester.

    Returns
    -------
    int
        The audit_id of the newly inserted row.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    details_json = json.dumps(details) if details is not None else None

    conn = get_db()
    try:
        cursor = conn.execute(
            """
            INSERT INTO audit_log (actor, action, target, details, ip_address, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (actor, action, target, details_json, ip, timestamp),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_audit_logs(
    page: int = 1,
    per_page: int = 20,
    actor: str | None = None,
    action: str | None = None,
) -> dict:
    """Return paginated audit log entries with optional filtering.

    Parameters
    ----------
    page : int
        Page number (1-indexed).
    per_page : int
        Number of entries per page.
    actor : str | None
        Filter by actor username.
    action : str | None
        Filter by action type.

    Returns
    -------
    dict
        {"logs": [...], "total": int, "page": int, "per_page": int}
    """
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    offset = (page - 1) * per_page

    conditions = []
    params = []

    if actor:
        conditions.append("actor = ?")
        params.append(actor)
    if action:
        conditions.append("action = ?")
        params.append(action)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    conn = get_db()
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM audit_log {where_clause}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT audit_id, actor, action, target, details, ip_address, timestamp
            FROM audit_log
            {where_clause}
            ORDER BY audit_id DESC
            LIMIT ? OFFSET ?
            """,
            params + [per_page, offset],
        ).fetchall()
    finally:
        conn.close()

    logs = []
    for row in rows:
        details_val = row["details"]
        if details_val:
            try:
                details_val = json.loads(details_val)
            except (json.JSONDecodeError, TypeError):
                pass  # Keep as string if not valid JSON

        logs.append({
            "audit_id": row["audit_id"],
            "actor": row["actor"],
            "action": row["action"],
            "target": row["target"],
            "details": details_val,
            "ip_address": row["ip_address"],
            "timestamp": row["timestamp"],
        })

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "per_page": per_page,
    }
