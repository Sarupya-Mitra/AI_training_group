"""Simple JWT login (educational version).

1. POST /auth/login  -> checks email + password in staff / employees, returns a token
2. Every protected endpoint reads the token to know WHO is calling:
     get_current_user -> any logged-in user (401 if no / bad token)
     require_staff    -> staff only (403 for employees)

Note: passwords are compared as plain text because the seed data stores them
that way. A real system would store bcrypt hashes instead.
"""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import config
from app.db import get_cursor

bearer = HTTPBearer(auto_error=False)


def authenticate(email, password):
    """Find the user in staff, then employees. Returns {email, name, role} or None."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT staff_name AS name, staff_email AS email FROM staff "
            "WHERE LOWER(staff_email) = LOWER(%s) AND staff_password = %s",
            (email, password),
        )
        row = cur.fetchone()
        if row:
            return {"email": row["email"], "name": row["name"], "role": "staff"}

        cur.execute(
            "SELECT emp_name AS name, emp_email AS email FROM employees "
            "WHERE LOWER(emp_email) = LOWER(%s) AND emp_password = %s",
            (email, password),
        )
        row = cur.fetchone()
        if row:
            return {"email": row["email"], "name": row["name"], "role": "employee"}
    return None


def create_token(user):
    payload = {
        "sub": user["email"],
        "name": user["name"],
        "role": user["role"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=config.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    """Read the token from the 'Authorization: Bearer <token>' header."""
    if creds is None:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        data = jwt.decode(creds.credentials, config.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired, please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"email": data["sub"], "name": data["name"], "role": data["role"]}


def require_staff(user=Depends(get_current_user)):
    if user["role"] != "staff":
        raise HTTPException(status_code=403, detail="Only support staff can do this")
    return user
