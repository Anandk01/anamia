"""
create_admin.py — One-off script to create an admin account in the Anemia DB.

Usage:
    python create_admin.py
"""

import bcrypt
from db import get_db


def create_admin():
    username = "admin"
    email = "admin@anemia.local"
    password = "Admin@123"
    role = "admin"

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=12)
    ).decode("utf-8")

    conn = get_db()
    try:
        # Check if admin already exists
        row = conn.execute(
            "SELECT user_id FROM user WHERE username = ?", (username,)
        ).fetchone()

        if row:
            print(f"Admin account '{username}' already exists (user_id={row['user_id']}).")
            return

        conn.execute(
            """
            INSERT INTO user (username, email, password_hash, role, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (username, email, password_hash, role),
        )
        conn.commit()
        print(f"Admin account created successfully!")
        print(f"  Username: {username}")
        print(f"  Email:    {email}")
        print(f"  Password: {password}")
        print(f"  Role:     {role}")
    finally:
        conn.close()


if __name__ == "__main__":
    create_admin()
