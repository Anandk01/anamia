"""
education_service.py — Business logic for the Education/Articles module.

Provides:
  create_article, generate_summary, publish_article,
  search_articles, toggle_bookmark
"""

from datetime import datetime, timezone

from db import get_db


def _row_to_dict(row):
    return dict(row) if row else {}


def _calc_read_time(content_md):
    """Estimate read time in minutes (avg 200 words/min)."""
    words = len(content_md.split())
    return max(1, round(words / 200))


def generate_summary(content_md):
    """Generate a simple summary from content (first 200 chars)."""
    if not content_md:
        return ""
    clean = content_md.replace('#', '').replace('*', '').strip()
    return clean[:200] + ('...' if len(clean) > 200 else '')


def create_article(author_id, title, content_md, tags=None):
    """Create a new draft article."""
    conn = get_db()
    try:
        read_time = _calc_read_time(content_md)
        summary = generate_summary(content_md)
        tags_str = ','.join(tags) if isinstance(tags, list) else tags

        cursor = conn.execute(
            """INSERT INTO article (title, content_md, summary, tags, author_id, read_time_min, status)
               VALUES (?, ?, ?, ?, ?, ?, 'draft')""",
            (title, content_md, summary, tags_str, author_id, read_time),
        )
        conn.commit()
        article = conn.execute(
            "SELECT * FROM article WHERE article_id = ?", (cursor.lastrowid,)
        ).fetchone()
        return _row_to_dict(article)
    finally:
        conn.close()


def publish_article(article_id, author_id):
    """Publish a draft article."""
    conn = get_db()
    try:
        article = conn.execute(
            "SELECT * FROM article WHERE article_id = ? AND author_id = ?",
            (article_id, author_id),
        ).fetchone()
        if not article:
            raise ValueError("Article not found or not owned by you.")
        if article["status"] == "published":
            raise ValueError("Article is already published.")

        published_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE article SET status = 'published', published_at = ? WHERE article_id = ?",
            (published_at, article_id),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM article WHERE article_id = ?", (article_id,)
        ).fetchone()
        return _row_to_dict(updated)
    finally:
        conn.close()


def search_articles(query=None, tag=None, page=1):
    """Search published articles by query or tag."""
    per_page = 20
    offset = (page - 1) * per_page

    conn = get_db()
    try:
        conditions = ["status = 'published'"]
        params = []

        if query:
            conditions.append("(title LIKE ? OR content_md LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        if tag:
            conditions.append("tags LIKE ?")
            params.append(f"%{tag}%")

        where = "WHERE " + " AND ".join(conditions)

        rows = conn.execute(
            f"""SELECT article_id, title, summary, tags, author_id, published_at, read_time_min
                FROM article {where}
                ORDER BY published_at DESC
                LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()

        total = conn.execute(
            f"SELECT COUNT(*) FROM article {where}", params
        ).fetchone()[0]

        return {"articles": [_row_to_dict(r) for r in rows], "total": total, "page": page}
    finally:
        conn.close()


def toggle_bookmark(username, article_id):
    """Toggle bookmark on an article."""
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT bookmark_id FROM bookmark WHERE username = ? AND article_id = ?",
            (username, article_id),
        ).fetchone()

        if existing:
            conn.execute("DELETE FROM bookmark WHERE bookmark_id = ?", (existing["bookmark_id"],))
            conn.commit()
            return {"bookmarked": False}
        else:
            conn.execute(
                "INSERT INTO bookmark (username, article_id) VALUES (?, ?)",
                (username, article_id),
            )
            conn.commit()
            return {"bookmarked": True}
    finally:
        conn.close()
