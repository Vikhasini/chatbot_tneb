# TNEB Official Email Support & Helpdesk Portal

A production-ready **Government Employee Self-Service Portal** for Tamil Nadu Electricity Board,
built with Flask + PostgreSQL and deployable to **Render Free Tier** with zero manual steps.

---

## ⚡ Deploy to Render (Step-by-Step)

### 1 — Push to GitHub
```bash
git init && git add . && git commit -m "initial"
git remote add origin https://github.com/YOU/tneb-portal.git
git push -u origin main
```

### 2 — Create a Render PostgreSQL Database
1. Render Dashboard → **New +** → **PostgreSQL**
2. Name: `tneb-db` | Plan: **Free**
3. Click **Create Database**
4. Copy the **Internal Database URL** (starts with `postgresql://`)

### 3 — Create a Render Web Service
1. Render Dashboard → **New +** → **Web Service**
2. Connect your GitHub repo
3. Settings:
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn run:app`
   - **Plan:** Free

### 4 — Set Environment Variables
In your Web Service → **Environment**:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | *(paste Internal Database URL from step 2)* |
| `SECRET_KEY` | *(any long random string)* |

### 5 — Deploy
Click **Manual Deploy → Deploy latest commit**.

The first deploy will:
1. Install dependencies
2. Connect to PostgreSQL
3. Create all tables automatically
4. Seed 50 employees, admin accounts, 100 tickets, etc.

**No shell access needed. No manual migrations.**

---

## 🔑 Default Login Credentials

| Role | Username | Password |
|------|----------|----------|
| Superadmin | `admin` | `admin123` |
| Admin | `admin01` – `admin09` | `Admin@1234` |
| Superadmin | `admin10` | `Admin@1234` |
| Employee | `EMP001` – `EMP020` | `Tneb@1234` |

---

## 🗂 Project Structure

```
tneb_portal/
├── run.py                   # Gunicorn entry point
├── config.py                # PostgreSQL config + Render URL fix
├── requirements.txt         # Flask, gunicorn, psycopg2-binary…
├── .env.example             # Environment variable template
├── seed/
│   └── seed_data.py         # Local-only manual seed (auto on Render)
└── app/
    ├── __init__.py          # App factory + auto DB init + seed
    ├── models/__init__.py   # SQLAlchemy models (PostgreSQL-compatible)
    ├── blueprints/
    │   ├── auth/            # Login / Logout
    │   ├── employee/        # Employee dashboard
    │   ├── chatbot/         # AI support chatbot
    │   ├── tickets/         # Ticket tracking
    │   └── admin/           # Admin panel
    ├── static/
    │   ├── css/portal.css
    │   └── js/{portal,chatbot}.js
    └── templates/
        ├── base.html
        ├── auth/login.html
        ├── employee/dashboard.html
        ├── chatbot/support.html
        ├── tickets/track.html
        └── admin/{dashboard,tickets,password_requests,employees}.html
```

---

## 💻 Local Development

```bash
# 1. Create and activate virtualenv
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start a local PostgreSQL instance (or use Render's external URL)
createdb tneb_portal

# 4. Set environment variables
cp .env.example .env
# Edit .env:  DATABASE_URL=postgresql://localhost/tneb_portal

# 5. Run
python run.py
# Tables and seed data are created automatically on first request.

# Optional: manual seed (resets all data)
python seed/seed_data.py
```

---

## 🌐 Endpoints

| URL | Description |
|-----|-------------|
| `/` | Redirect to login |
| `/auth/login` | Login page |
| `/auth/logout` | Logout |
| `/employee/dashboard` | Employee home |
| `/chatbot/support` | AI support assistant |
| `/tickets/track` | Ticket tracker |
| `/admin/dashboard` | Admin overview + charts |
| `/admin/tickets` | Ticket management |
| `/admin/password-requests` | Password reset approvals |
| `/admin/employees` | Employee directory |
| `/health` | Health check (for Render) |

---

## 🔧 PostgreSQL Notes

- Render provides a `postgres://` URL; the app automatically rewrites it to `postgresql://` for SQLAlchemy.
- Connection pooling is configured with `pool_pre_ping=True` and `pool_recycle=300s` to survive Render's free-tier idle disconnections.
- All models use standard SQLAlchemy types — no MySQL or SQLite-specific code remains.

---

© 2025 Tamil Nadu Electricity Board — Internal Use Only
