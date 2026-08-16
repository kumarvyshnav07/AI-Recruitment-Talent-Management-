import bcrypt
import streamlit as st
from database import get_connection, DB_CONFIG


# -----------------------------
# Register User
# -----------------------------
def register(username, email, password, role="candidate"):
    connection = get_connection()
    if connection is None:
        return False, "Database connection failed"

    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE username=%s OR email=%s",
        (username, email),
    )

    if cursor.fetchone():
        cursor.close()
        connection.close()
        return False, "User already exists"

    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    cursor.execute(
        "INSERT INTO users(username, email, password, role) VALUES (%s, %s, %s, %s)",
        (username, email, hashed_password.decode(), role),
    )

    connection.commit()
    cursor.close()
    connection.close()

    return True, "Registration Successful"


# -----------------------------
# Login User
# -----------------------------
def login(username, password):
    connection = get_connection()
    if connection is None:
        return None

    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
    row = cursor.fetchone()

    cursor.close()
    connection.close()

    if row is None:
        return None

    if bcrypt.checkpw(password.encode(), row["password"].encode()):
        return row
    return None
