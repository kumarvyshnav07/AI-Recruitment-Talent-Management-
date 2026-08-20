"""
create_admin.py
================
One-time command-line setup script for TalentOps AI's Admin Control
Center. Run this once to create the platform's first admin account.

Why this exists as a script instead of a button in the app: the Admin
portal's login screen deliberately has no "Create Account" tab —
letting anyone self-register as admin from the public login page would
defeat the whole point of role-based access control. After the first
admin exists, every additional admin should be granted through the
running app itself (Admin → Users → change a user's role to Admin),
which is authenticated and audit-logged. This script is only for
bootstrapping account #1.

Usage:
    python create_admin.py

You'll be prompted for a username, email, and password. If a user with
that username/email already exists, this promotes it to admin (and
activates it) instead of failing.
"""
import getpass

from database import init_db
from admin_db import init_admin_db
import auth


def main():
    print("=== TalentOps AI — Create Admin Account ===\n")

    init_db()
    init_admin_db()

    username = input("Admin username: ").strip()
    email = input("Admin email: ").strip()

    if not username or not email:
        print("Username and email are required. Aborting.")
        return

    password = getpass.getpass("Admin password: ")
    confirm = getpass.getpass("Confirm password: ")

    if not password:
        print("Password cannot be empty. Aborting.")
        return
    if password != confirm:
        print("Passwords do not match. Aborting.")
        return

    ok, msg = auth.register(username, email, password, role="admin")

    if ok:
        print(f"\n✅ {msg} — '{username}' can now sign in through the Admin portal.")
        return

    # Already exists (by username or email) — offer to promote it instead
    # of just failing, since "user already exists" is the expected path
    # the second time this script is run, or if the account was created
    # through a normal portal first.
    print(f"\n⚠️  {msg}")
    promote = input("Promote this existing account to admin instead? (y/N): ").strip().lower()
    if promote != "y":
        print("No changes made.")
        return

    import admin_db as adb
    from database import get_connection, DB_CONFIG

    conn = get_connection()
    if conn is None:
        print("Could not connect to the database.")
        return
    conn.database = DB_CONFIG["database"]
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username FROM users WHERE username=%s OR email=%s", (username, email))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        print("Could not find that account. Aborting.")
        return

    adb.set_user_role(row["id"], "admin")
    adb.set_user_status(row["id"], "active")
    print(f"\n✅ '{row['username']}' has been promoted to admin and activated.")


if __name__ == "__main__":
    main()