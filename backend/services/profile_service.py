"""
profile_service.py — User profile management.

Provides:
  get_profile, update_health_profile, update_preferences,
  update_available_hours, change_password
"""

import json

import bcrypt

from db import get_db


def get_profile(username):
    """Get full user profile."""
    conn = get_db()
    try:
        row = conn.execute(
            """SELECT user_id, username, email, role, status, language_pref,
                      vegan_diet, age, sex, blood_type, known_conditions,
                      dietary_preferences, emergency_contact, specialization,
                      license_number, available_hours, notification_prefs,
                      theme_pref, font_size, high_contrast, created_at
               FROM user WHERE username = ?""",
            (username,),
        ).fetchone()
        if not row:
            return None
        profile = dict(row)
        # Parse JSON fields
        for field in ['available_hours', 'notification_prefs']:
            if profile.get(field):
                try:
                    profile[field] = json.loads(profile[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return profile
    finally:
        conn.close()


def update_health_profile(username, data):
    """Update health-related profile fields."""
    allowed = ['blood_type', 'known_conditions', 'dietary_preferences',
               'emergency_contact', 'vegan_diet', 'age', 'sex']
    conn = get_db()
    try:
        updates = []
        params = []
        for key in allowed:
            if key in data:
                updates.append(f"{key} = ?")
                params.append(data[key])

        if not updates:
            return get_profile(username)

        params.append(username)
        conn.execute(
            f"UPDATE user SET {', '.join(updates)} WHERE username = ?",
            params,
        )
        conn.commit()
        return get_profile(username)
    finally:
        conn.close()


def update_preferences(username, prefs):
    """Update user preferences (theme, font, language, notifications)."""
    conn = get_db()
    try:
        updates = []
        params = []

        if 'language_pref' in prefs:
            updates.append("language_pref = ?")
            params.append(prefs['language_pref'])
        if 'theme_pref' in prefs:
            updates.append("theme_pref = ?")
            params.append(prefs['theme_pref'])
        if 'font_size' in prefs:
            updates.append("font_size = ?")
            params.append(prefs['font_size'])
        if 'high_contrast' in prefs:
            updates.append("high_contrast = ?")
            params.append(1 if prefs['high_contrast'] else 0)
        if 'notification_prefs' in prefs:
            updates.append("notification_prefs = ?")
            params.append(json.dumps(prefs['notification_prefs']))

        if not updates:
            return get_profile(username)

        params.append(username)
        conn.execute(
            f"UPDATE user SET {', '.join(updates)} WHERE username = ?",
            params,
        )
        conn.commit()
        return get_profile(username)
    finally:
        conn.close()


def update_available_hours(username, hours):
    """Update doctor's available hours. hours is a dict like {"mon": {"start":"09:00","end":"17:00"}}."""
    conn = get_db()
    try:
        hours_json = json.dumps(hours) if isinstance(hours, dict) else hours
        conn.execute(
            "UPDATE user SET available_hours = ? WHERE username = ?",
            (hours_json, username),
        )
        conn.commit()
        return get_profile(username)
    finally:
        conn.close()


def change_password(username, current_password, new_password):
    """Change user password after verifying current password."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT password_hash FROM user WHERE username = ?",
            (username,),
        ).fetchone()
        if not row:
            raise ValueError("User not found.")

        if not bcrypt.checkpw(
            current_password.encode('utf-8'),
            row['password_hash'].encode('utf-8'),
        ):
            raise ValueError("Current password is incorrect.")

        new_hash = bcrypt.hashpw(
            new_password.encode('utf-8'),
            bcrypt.gensalt(rounds=12),
        ).decode('utf-8')

        conn.execute(
            "UPDATE user SET password_hash = ? WHERE username = ?",
            (new_hash, username),
        )
        conn.commit()
        return {"changed": True}
    finally:
        conn.close()
