"""
forum_service.py — Business logic for the Community Forum module.

Provides:
  create_post, get_posts, upvote_post, create_reply,
  upvote_reply, verify_reply, delete_post
"""

from datetime import datetime, timezone

from db import get_db


def _row_to_dict(row):
    return dict(row) if row else {}


def create_post(username, title, body, tags=None, anonymous=False):
    """Create a new forum post."""
    conn = get_db()
    try:
        tags_str = ','.join(tags) if isinstance(tags, list) else tags
        cursor = conn.execute(
            """INSERT INTO post (username, title, body, tags, anonymous, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username, title, body, tags_str, 1 if anonymous else 0,
             datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        post = conn.execute("SELECT * FROM post WHERE post_id = ?", (cursor.lastrowid,)).fetchone()
        return _row_to_dict(post)
    finally:
        conn.close()


def get_posts(sort='new', page=1, tag=None):
    """Get paginated posts with hot ranking support."""
    per_page = 20
    offset = (page - 1) * per_page

    conn = get_db()
    try:
        conditions = []
        params = []

        if tag:
            conditions.append("tags LIKE ?")
            params.append(f"%{tag}%")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        if sort == 'hot':
            rows = conn.execute(
                f"""SELECT *, (upvotes * 1.0) / POWER(
                    (julianday('now') - julianday(created_at)) * 24 + 2, 1.5
                ) AS hot_score
                FROM post {where}
                ORDER BY pinned DESC, hot_score DESC
                LIMIT ? OFFSET ?""",
                params + [per_page, offset],
            ).fetchall()
        else:
            rows = conn.execute(
                f"""SELECT * FROM post {where}
                    ORDER BY pinned DESC, created_at DESC
                    LIMIT ? OFFSET ?""",
                params + [per_page, offset],
            ).fetchall()

        total = conn.execute(f"SELECT COUNT(*) FROM post {where}", params).fetchone()[0]
        posts = [_row_to_dict(r) for r in rows]
        return {"posts": posts, "total": total, "page": page}
    finally:
        conn.close()


def upvote_post(post_id, username):
    """Toggle upvote on a post."""
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM post_upvote WHERE post_id = ? AND username = ?",
            (post_id, username),
        ).fetchone()

        if existing:
            conn.execute("DELETE FROM post_upvote WHERE id = ?", (existing["id"],))
            conn.execute("UPDATE post SET upvotes = upvotes - 1 WHERE post_id = ?", (post_id,))
            action = "removed"
        else:
            conn.execute(
                "INSERT INTO post_upvote (post_id, username) VALUES (?, ?)",
                (post_id, username),
            )
            conn.execute("UPDATE post SET upvotes = upvotes + 1 WHERE post_id = ?", (post_id,))
            action = "added"

        conn.commit()
        post = conn.execute("SELECT upvotes FROM post WHERE post_id = ?", (post_id,)).fetchone()
        return {"action": action, "upvotes": post["upvotes"] if post else 0}
    finally:
        conn.close()


def create_reply(post_id, username, body):
    """Create a reply on a post."""
    conn = get_db()
    try:
        # Verify post exists
        post = conn.execute("SELECT post_id FROM post WHERE post_id = ?", (post_id,)).fetchone()
        if not post:
            raise ValueError("Post not found.")

        cursor = conn.execute(
            """INSERT INTO reply (post_id, username, body, created_at)
               VALUES (?, ?, ?, ?)""",
            (post_id, username, body,
             datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        reply = conn.execute("SELECT * FROM reply WHERE reply_id = ?", (cursor.lastrowid,)).fetchone()
        return _row_to_dict(reply)
    finally:
        conn.close()


def upvote_reply(reply_id, username):
    """Toggle upvote on a reply."""
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM reply_upvote WHERE reply_id = ? AND username = ?",
            (reply_id, username),
        ).fetchone()

        if existing:
            conn.execute("DELETE FROM reply_upvote WHERE id = ?", (existing["id"],))
            conn.execute("UPDATE reply SET upvotes = upvotes - 1 WHERE reply_id = ?", (reply_id,))
            action = "removed"
        else:
            conn.execute(
                "INSERT INTO reply_upvote (reply_id, username) VALUES (?, ?)",
                (reply_id, username),
            )
            conn.execute("UPDATE reply SET upvotes = upvotes + 1 WHERE reply_id = ?", (reply_id,))
            action = "added"

        conn.commit()
        reply = conn.execute("SELECT upvotes FROM reply WHERE reply_id = ?", (reply_id,)).fetchone()
        return {"action": action, "upvotes": reply["upvotes"] if reply else 0}
    finally:
        conn.close()


def verify_reply(reply_id, doctor_username):
    """Mark a reply as doctor-verified."""
    conn = get_db()
    try:
        # Verify doctor exists
        doctor = conn.execute(
            "SELECT username FROM user WHERE username = ? AND role = 'doctor'",
            (doctor_username,),
        ).fetchone()
        if not doctor:
            raise ValueError("Only doctors can verify replies.")

        conn.execute(
            "UPDATE reply SET is_doctor_verified = 1 WHERE reply_id = ?",
            (reply_id,),
        )
        conn.commit()
        reply = conn.execute("SELECT * FROM reply WHERE reply_id = ?", (reply_id,)).fetchone()
        return _row_to_dict(reply)
    finally:
        conn.close()


def delete_post(post_id, username, is_admin=False):
    """Delete a post (only author or admin)."""
    conn = get_db()
    try:
        post = conn.execute("SELECT * FROM post WHERE post_id = ?", (post_id,)).fetchone()
        if not post:
            raise ValueError("Post not found.")

        if not is_admin and post["username"] != username:
            raise ValueError("Not authorized to delete this post.")

        # Delete replies and upvotes first
        conn.execute("DELETE FROM reply_upvote WHERE reply_id IN (SELECT reply_id FROM reply WHERE post_id = ?)", (post_id,))
        conn.execute("DELETE FROM reply WHERE post_id = ?", (post_id,))
        conn.execute("DELETE FROM post_upvote WHERE post_id = ?", (post_id,))
        conn.execute("DELETE FROM post WHERE post_id = ?", (post_id,))
        conn.commit()
        return {"deleted": True}
    finally:
        conn.close()
