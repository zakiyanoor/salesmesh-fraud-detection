"""
Authentication module for the SalesMesh fraud detection system.

Implements FR-01 (login before accessing dashboard functions) and NFR-02
(only authenticated users access protected routes), per Deliverable 3.6.2:
username/password authentication with hashed password storage, session
management, and role-based access control.

Adds the Administrator entity (not explicitly in the original ERD, but
required to support login) and a login_required decorator that protects
any Flask route it is applied to.
"""

from functools import wraps
from flask import session, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, String
from src.db import Base, get_session, engine


class Administrator(Base):
    __tablename__ = "administrators"

    admin_id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="administrator")


def create_admin_table():
    """Creates the administrators table if it does not already exist."""
    Base.metadata.create_all(engine, tables=[Administrator.__table__])
    print("Administrators table created successfully.")


def create_admin_user(admin_id, username, password, role="administrator"):
    db_session = get_session()
    try:
        existing = db_session.query(Administrator).filter(Administrator.username == username).first()
        if existing:
            print(f"Username '{username}' already exists.")
            return

        admin = Administrator(
            admin_id=admin_id,
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
        )
        db_session.add(admin)
        db_session.commit()
        print(f"Administrator '{username}' created successfully.")
    finally:
        db_session.close()


def verify_login(username, password):
    db_session = get_session()
    try:
        admin = db_session.query(Administrator).filter(Administrator.username == username).first()
        if admin and check_password_hash(admin.password_hash, password):
            return {"admin_id": admin.admin_id, "username": admin.username, "role": admin.role}
        return None
    finally:
        db_session.close()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated


if __name__ == "__main__":
    create_admin_table()
    create_admin_user(admin_id="ADM001", username="admin", password="ChangeMe123!")