import bcrypt
from database import get_connection, DB_CONFIG


# -----------------------------
# Register User
# -----------------------------
def register(username, email, password):
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
        "INSERT INTO users(username, email, password) VALUES (%s, %s, %s)",
        (username, email, hashed_password.decode()),
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
        return False

    connection.database = DB_CONFIG["database"]
    cursor = connection.cursor()

    cursor.execute("SELECT password FROM users WHERE username=%s", (username,))
    row = cursor.fetchone()

    cursor.close()
    connection.close()

    # NOTE: no account found -> login fails. (A previous version of this
    # file had a hardcoded bypass that let anyone log in as "Recruiter"
    # with any password — that's a serious auth vulnerability and has
    # been removed. Every user must register a real account.)
    if row is None:
        return False

    return bcrypt.checkpw(password.encode(), row[0].encode())