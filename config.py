import os
import sys
from dotenv import load_dotenv

load_dotenv()


def get_database_url():
    """
    Resolve the PostgreSQL connection URL for psycopg v3.

    Render gives DATABASE_URL as:  postgres://...   or  postgresql://...
    SQLAlchemy + psycopg v3 needs: postgresql+psycopg://...

    We handle all four possible incoming prefixes:
      postgres://            → postgresql+psycopg://
      postgresql://          → postgresql+psycopg://
      postgres+psycopg://    → postgresql+psycopg://   (already correct dialect, fix scheme)
      postgresql+psycopg://  → unchanged (already correct)
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print(
            "[TNEB] FATAL: DATABASE_URL environment variable is not set.\n"
            "       Set it to your Render PostgreSQL connection string before starting.",
            file=sys.stderr,
        )
        return "postgresql+psycopg://localhost/tneb_missing"

    # Normalise to postgresql+psycopg:// (psycopg v3 SQLAlchemy driver)
    replacements = [
        ("postgres+psycopg://",   "postgresql+psycopg://"),   # wrong scheme, right dialect
        ("postgresql://",          "postgresql+psycopg://"),   # old psycopg2 style
        ("postgres://",            "postgresql+psycopg://"),   # Render shorthand
    ]
    for old, new in replacements:
        if url.startswith(old):
            url = new + url[len(old):]
            break

    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "tneb-portal-fallback-key-change-in-prod")
    SQLALCHEMY_DATABASE_URI = get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        # Keep connections alive on Render's free tier (which idles)
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 2,
    }
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": ProductionConfig,   # Render uses default
}
