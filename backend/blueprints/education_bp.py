"""
Education Blueprint — /api/articles

Educational articles with bookmarking support.
"""

from flask import Blueprint, g, jsonify, request

from db import get_db
from middleware.auth import require_auth
from middleware.rbac import require_role
from services import education_service

education_bp = Blueprint("education", __name__, url_prefix="/api/articles")


@education_bp.get("/")
@require_auth
def list_articles():
    query = request.args.get("query")
    tag = request.args.get("tag")
    page = int(request.args.get("page", 1))
    result = education_service.search_articles(query=query, tag=tag, page=page)
    return jsonify({"status": "ok", **result}), 200


@education_bp.post("/")
@require_auth
@require_role("doctor", "admin")
def create_article():
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    content_md = data.get("content_md", "").strip()
    if not title or not content_md:
        return jsonify({"status": "error", "message": "title and content_md required"}), 400
    tags = data.get("tags")
    author_id = g.current_user["username"]
    article = education_service.create_article(author_id, title, content_md, tags)
    return jsonify({"status": "ok", "article": article}), 201


@education_bp.get("/<int:article_id>")
@require_auth
def get_article(article_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM article WHERE article_id = ?", (article_id,)
        ).fetchone()
        if not row:
            return jsonify({"status": "error", "message": "Article not found"}), 404
        return jsonify({"status": "ok", "article": dict(row)}), 200
    finally:
        conn.close()


@education_bp.put("/<int:article_id>")
@require_auth
@require_role("doctor", "admin")
def update_article(article_id):
    data = request.get_json(silent=True) or {}
    author_id = g.current_user["username"]
    conn = get_db()
    try:
        article = conn.execute(
            "SELECT * FROM article WHERE article_id = ? AND author_id = ?",
            (article_id, author_id),
        ).fetchone()
        if not article:
            return jsonify({"status": "error", "message": "Article not found or not yours"}), 404

        title = data.get("title", article["title"])
        content_md = data.get("content_md", article["content_md"])
        tags = data.get("tags", article["tags"])
        if isinstance(tags, list):
            tags = ','.join(tags)

        read_time = max(1, round(len(content_md.split()) / 200))
        summary = education_service.generate_summary(content_md)

        conn.execute(
            """UPDATE article SET title=?, content_md=?, summary=?, tags=?, read_time_min=?
               WHERE article_id=?""",
            (title, content_md, summary, tags, read_time, article_id),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM article WHERE article_id = ?", (article_id,)
        ).fetchone()
        return jsonify({"status": "ok", "article": dict(updated)}), 200
    finally:
        conn.close()


@education_bp.post("/<int:article_id>/publish")
@require_auth
@require_role("doctor", "admin")
def publish_article(article_id):
    author_id = g.current_user["username"]
    try:
        article = education_service.publish_article(article_id, author_id)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    return jsonify({"status": "ok", "article": article}), 200


@education_bp.post("/<int:article_id>/bookmark")
@require_auth
def bookmark_article(article_id):
    username = g.current_user["username"]
    result = education_service.toggle_bookmark(username, article_id)
    return jsonify({"status": "ok", **result}), 200


@education_bp.get("/bookmarks")
@require_auth
def get_bookmarks():
    username = g.current_user["username"]
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT a.* FROM article a
               JOIN bookmark b ON b.article_id = a.article_id
               WHERE b.username = ?
               ORDER BY b.created_at DESC""",
            (username,),
        ).fetchall()
        return jsonify({"status": "ok", "articles": [dict(r) for r in rows]}), 200
    finally:
        conn.close()
