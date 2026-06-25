# TNEB Digital Helpdesk — Local Setup Guide

Run the full project on your local machine before deploying to Render.

---

## Option A — With Local PostgreSQL (Recommended)

### 1. Install PostgreSQL
**Windows:** Download from https://www.postgresql.org/download/windows/
**Mac:** `brew install postgresql@16 && brew services start postgresql@16`
**Ubuntu/WSL:** `sudo apt install postgresql postgresql-contrib && sudo service postgresql start`

### 2. Create the database
```bash
# Log in to psql
psql -U postgres

# Inside psql:
CREATE DATABASE tneb_portal;
\q
```

### 3. Clone / extract the project
```bash
cd tneb_portal
```

### 4. Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux / WSL
source venv/bin/activate
```

### 5. Install dependencies
```bash
pip install -r requirements.txt
```

### 6. Configure `.env`
The `.env` file is already created. Edit it if your Postgres password is different:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost/tneb_portal
SECRET_KEY=any-long-random-string
FLASK_ENV=development
```

### 7. Run the application
```bash
python run.py
```

On first run, the app will:
- Connect to PostgreSQL
- Create all tables automatically
- Seed 50 employees, 10 admins, 100 tickets, etc.

### 8. Open the browser
```
http://localhost:5000
```

---

## Option B — Without Local PostgreSQL (Use Render DB Remotely)

If you don't want to install PostgreSQL locally, you can use your Render PostgreSQL from your local machine.

### 1. Create a Render PostgreSQL (Free)
- Render Dashboard → New + → PostgreSQL → Free
- Copy the **External Database URL** (not Internal — Internal only works on Render servers)

### 2. Set DATABASE_URL in `.env`
```
DATABASE_URL=postgresql://user:pass@dpg-xxxx.render.com/tneb_portal
```

### 3. Run normally
```bash
python run.py
```

Tables are created and seeded automatically on first run.

> ⚠️ Note: The free Render PostgreSQL sleeps after 5 minutes of inactivity.
> Your first query after idle may take 5–10 seconds to reconnect. This is normal.

---

## Login Credentials (after seed)

| Role        | Username       | Password     |
|-------------|----------------|--------------|
| Superadmin  | `admin`        | `admin123`   |
| Admin       | `admin01`–`admin09` | `Admin@1234` |
| Superadmin  | `admin10`      | `Admin@1234` |
| Employee    | `EMP001`–`EMP020`   | `Tneb@1234`  |

---

## Page Map

| URL                              | Description                  | Access     |
|----------------------------------|------------------------------|------------|
| `http://localhost:5000/`         | Public Home                  | Public     |
| `/helpdesk`                      | Public Chatbot               | Public     |
| `/track`                         | Track Ticket (no login)      | Public     |
| `/faq`                           | FAQ                          | Public     |
| `/forgot-password`               | Password Reset Form          | Public     |
| `/request-email`                 | Request Official Email       | Public     |
| `/auth/login`                    | Login Page                   | Public     |
| `/employee/dashboard`            | Employee Dashboard           | Employee   |
| `/employee/raise-ticket`         | Raise Support Ticket         | Employee   |
| `/employee/tickets`              | My Ticket History            | Employee   |
| `/chatbot/support`               | Employee Chat                | Employee   |
| `/admin/dashboard`               | Admin Overview               | Admin      |
| `/admin/notifications`           | All Notifications            | Admin      |
| `/admin/tickets`                 | Ticket Management            | Admin      |
| `/admin/password-requests`       | Password Reset Approvals     | Admin      |
| `/admin/email-requests`          | Email Request Approvals      | Admin      |
| `/admin/employees`               | Employee Directory           | Admin      |
| `/health`                        | Health check (for Render)    | Public     |

---

## Re-seed / Reset Data

To wipe all data and re-seed from scratch:
```bash
# Run the manual seed script (drops and recreates all tables)
python seed/seed_data.py
```

⚠️ This deletes everything. Only use on development.

---

## Deploy to Render

When you're happy with local testing:

1. Push to GitHub: `git add . && git commit -m "ready" && git push`
2. Render → New Web Service → connect repo
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn run:app`
3. Set env vars: `DATABASE_URL` (Internal URL) + `SECRET_KEY`
4. Deploy — tables and seed data created automatically.

See `README.md` for full Render deployment steps.
