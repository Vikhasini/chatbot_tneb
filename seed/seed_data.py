"""
seed_data.py — Manual seed script for local development.

For Render deployments, seeding happens automatically inside
app/__init__.py on first startup — you do NOT need to run this.

Local usage:
    export DATABASE_URL=postgresql://user:pass@localhost/tneb_portal
    python seed/seed_data.py

WARNING: This script DROPS and RECREATES all tables.
         Never run against a production database.
"""
import sys
import os

# Allow running from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("FLASK_ENV", "development")

from app import create_app, db, _seed_users, _seed_all
from app.models import Employee

app = create_app("development")

with app.app_context():
    print("Dropping all tables …")
    db.drop_all()
    print("Creating all tables …")
    db.create_all()

    print("Seeding users …")
    _seed_users()

    print("Seeding employees, tickets, etc. …")
    _seed_all()

    print("\n✅  Seed complete.")
    print("   Employee logins : EMP001–EMP020  / Tneb@1234")
    print("   Admin logins    : admin01–admin09 / Admin@1234")
    print("   Superadmin      : admin / admin123  |  admin10 / Admin@1234")
