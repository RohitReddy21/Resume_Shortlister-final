"""Seed an initial admin user for development.

Usage:
    python scripts/seed_admin.py --email admin@example.com --password secret

This script uses the same SQLAlchemy settings as the app and creates a user with role Admin.
"""
import argparse
import os
import sys
from pathlib import Path

# Ensure package imports work when running this script directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal, init_db
from app.core.config import get_settings
from app.core.security import get_password_hash
from app.crud.user import get_user_by_email, create_user


def main():
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=settings.admin_email)
    parser.add_argument("--password", default=settings.admin_password)
    parser.add_argument("--full-name", default="Administrator")
    args = parser.parse_args()

    if not args.email or not args.password:
        parser.error("email and password are required, either as arguments or ADMIN_EMAIL/ADMIN_PASSWORD in .env")

    # Ensure DB and tables exist
    init_db()

    db = SessionLocal()
    try:
        existing = get_user_by_email(db, args.email)
        if existing:
            existing.password_hash = get_password_hash(args.password)
            existing.role = "Admin"
            existing.is_active = True
            db.commit()
            print(f"Updated admin user {args.email} (id={existing.id})")
            return

        user = create_user(db, args.email, args.full_name, args.password, role="Admin")
        print(f"Created admin user {user.email} (id={user.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
