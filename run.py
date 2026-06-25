"""
run.py — TNEB Email Support Portal
Entry point for both local dev and Render (gunicorn run:app).

Render start command: gunicorn run:app
Local dev:            python run.py
"""
import os
import sys

# Validate DATABASE_URL early so the error is obvious
db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    print(
        "\n[TNEB] ❌  DATABASE_URL is not set.\n"
        "       Add it in Render → Environment → DATABASE_URL\n"
        "       (copy the Internal Database URL from your Render PostgreSQL service)\n",
        file=sys.stderr,
    )
    # Don't exit — let the app start so the health endpoint is reachable
    # and Render doesn't mark the deploy as crashed immediately.

from app import create_app

# Render sets FLASK_ENV=production; locally defaults to development
config_name = os.environ.get("FLASK_ENV", "production")
app = create_app(config_name)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=(config_name == "development"))
