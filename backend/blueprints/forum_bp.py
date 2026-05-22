"""
Forum Blueprint — /api/forum

Community forum with posts, replies, upvotes, and doctor verification.
"""

from flask import Blueprint, g, jsonify, request

from db import get_db
from middleware.auth import require_auth
from middleware.rbac import require_role
from services import forum_service

forum_bp = Blueprint("forum", __name__, url_prefix="/api/forum")


@forum_bp.get("/posts")
@require_auth
def get_posts():
    sort = request.args.get("sort", "new")
    page = int(request.args.get("page", 1))
    tag = request.args.get("tag")
    result = forum_service.get_posts(sort=sort, page=page, tag=tag)
    return jsonify({"status": "ok", **result}), 200


@forum_bp.post("/posts")
@require_auth
def create_post():
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    body = data.get("body", "").strip()
    if not title or not body:
        return jsonify({"status": "error", "message": "title and body required"}), 400
    tags = data.get("tags")
    anonymous = data.get("anonymous", False)
    username = g.current_user["username"]
    post = forum_service.create_post(username, title, body, tags, anonymous)
    return jsonify({"status": "ok", "post": post}), 201


@forum_bp.get("/posts/<int:post_id>")
@require_auth
def get_post(post_id):
    conn = get_db()
    try:
        post = conn.execute("SELECT * FROM post WHERE post_id = ?", (post_id,)).fetchone()
        if not post:
            return jsonify({"status": "error", "message": "Post not found"}), 404
        replies = conn.execute(
            "SELECT * FROM reply WHERE post_id = ? ORDER BY created_at ASC",
            (post_id,),
        ).fetchall()
        return jsonify({
            "status": "ok",
            "post": dict(post),
            "replies": [dict(r) for r in replies],
        }), 200
    finally:
        conn.close()


@forum_bp.post("/posts/<int:post_id>/replies")
@require_auth
def create_reply(post_id):
    data = request.get_json(silent=True) or {}
    body = data.get("body", "").strip()
    if not body:
        return jsonify({"status": "error", "message": "body required"}), 400
    username = g.current_user["username"]
    try:
        reply = forum_service.create_reply(post_id, username, body)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    return jsonify({"status": "ok", "reply": reply}), 201


@forum_bp.post("/posts/<int:post_id>/upvote")
@require_auth
def upvote_post(post_id):
    username = g.current_user["username"]
    result = forum_service.upvote_post(post_id, username)
    return jsonify({"status": "ok", **result}), 200


@forum_bp.post("/replies/<int:reply_id>/upvote")
@require_auth
def upvote_reply(reply_id):
    username = g.current_user["username"]
    result = forum_service.upvote_reply(reply_id, username)
    return jsonify({"status": "ok", **result}), 200


@forum_bp.put("/replies/<int:reply_id>/verify")
@require_auth
@require_role("doctor")
def verify_reply(reply_id):
    username = g.current_user["username"]
    try:
        reply = forum_service.verify_reply(reply_id, username)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    return jsonify({"status": "ok", "reply": reply}), 200


@forum_bp.delete("/posts/<int:post_id>")
@require_auth
def delete_post(post_id):
    username = g.current_user["username"]
    role = g.current_user["role"]
    try:
        result = forum_service.delete_post(post_id, username, is_admin=(role == 'admin'))
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 403
    return jsonify({"status": "ok", **result}), 200


@forum_bp.get("/tags")
@require_auth
def get_tags():
    conn = get_db()
    try:
        rows = conn.execute("SELECT DISTINCT tags FROM post WHERE tags IS NOT NULL").fetchall()
        all_tags = set()
        for row in rows:
            if row["tags"]:
                for tag in row["tags"].split(","):
                    tag = tag.strip()
                    if tag:
                        all_tags.add(tag)
        return jsonify({"status": "ok", "tags": sorted(all_tags)}), 200
    finally:
        conn.close()
