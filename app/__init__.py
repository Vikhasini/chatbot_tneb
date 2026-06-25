import os, sys, logging, random
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("tneb")

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "production")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # ── Blueprints ──────────────────────────────────────────
    from app.blueprints.public      import public      as public_bp
    from app.blueprints.auth        import auth        as auth_bp
    from app.blueprints.employee    import employee    as employee_bp
    from app.blueprints.admin       import admin       as admin_bp
    from app.blueprints.chatbot     import chatbot     as chatbot_bp
    from app.blueprints.tickets     import tickets     as tickets_bp
    from app.blueprints.notifications import notifications as notif_bp

    app.register_blueprint(public_bp,    url_prefix="/")
    app.register_blueprint(auth_bp,      url_prefix="/auth")
    app.register_blueprint(employee_bp,  url_prefix="/employee")
    app.register_blueprint(admin_bp,     url_prefix="/admin")
    app.register_blueprint(chatbot_bp,   url_prefix="/chatbot")
    app.register_blueprint(tickets_bp,   url_prefix="/tickets")
    app.register_blueprint(notif_bp,     url_prefix="/notifications")

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    # ── DB init at startup ──────────────────────────────────
    with app.app_context():
        try:
            log.info("Running db.create_all() …")
            db.create_all()
            log.info("Tables ready.")
            from app.models import User, Employee
            if User.query.count() == 0:
                _seed_users()
            if Employee.query.count() == 0:
                _seed_all()
        except Exception as exc:
            log.error("DB init failed: %s", exc, exc_info=True)
            raise

    return app


# ── Seed helpers ──────────────────────────────────────────────────────────────

def _seed_users():
    from app.models import User
    defaults = [
        ("admin",   "admin@tneb.in",   "admin123",   "superadmin"),
        ("admin01", "admin01@tneb.in", "Admin@1234", "admin"),
        ("admin02", "admin02@tneb.in", "Admin@1234", "admin"),
        ("admin03", "admin03@tneb.in", "Admin@1234", "admin"),
        ("admin04", "admin04@tneb.in", "Admin@1234", "admin"),
        ("admin05", "admin05@tneb.in", "Admin@1234", "admin"),
        ("admin06", "admin06@tneb.in", "Admin@1234", "admin"),
        ("admin07", "admin07@tneb.in", "Admin@1234", "admin"),
        ("admin08", "admin08@tneb.in", "Admin@1234", "admin"),
        ("admin09", "admin09@tneb.in", "Admin@1234", "admin"),
        ("admin10", "admin10@tneb.in", "Admin@1234", "superadmin"),
    ]
    for username, email, password, role in defaults:
        if not User.query.filter_by(username=username).first():
            u = User(username=username, email=email, role=role, is_active=True)
            u.set_password(password)
            db.session.add(u)
    db.session.commit()
    log.info("Admin accounts created.")


def _seed_all():
    import random
    from datetime import datetime, timedelta
    from app.models import (Employee, OfficialEmail, User, SupportTicket,
                            PasswordResetRequest, EmailRequest, Notification)

    DISTRICTS = ["Chennai","Coimbatore","Madurai","Salem","Trichy",
                 "Tirunelveli","Vellore","Erode","Thoothukudi","Tiruppur"]
    DESIGNATIONS = ["Junior Engineer","Assistant Engineer","Divisional Engineer",
                    "Executive Engineer","Superintending Engineer","Chief Engineer"]
    DEPARTMENTS = ["Distribution","Transmission","Generation",
                   "Finance","HR & Admin","Operations & Maintenance"]
    OFFICES = {
        "Chennai":     ["Anna Nagar Sub-Division","T. Nagar Division","Guindy Circle"],
        "Coimbatore":  ["RS Puram Sub-Division","Gandhipuram Division","Peelamedu Circle"],
        "Madurai":     ["Anna Nagar Sub-Division","Pasumalai Division","Madurai Central Circle"],
        "Salem":       ["Salem North Sub-Division","Attur Division","Salem Circle"],
        "Trichy":      ["Srirangam Sub-Division","Trichy Central Division","Golden Rock Circle"],
        "Tirunelveli": ["Palayamkottai Sub-Division","Tirunelveli Division","South Circle"],
        "Vellore":     ["Vellore Sub-Division","Katpadi Division","Vellore Circle"],
        "Erode":       ["Erode Sub-Division","Bhavani Division","Erode Circle"],
        "Thoothukudi": ["Thoothukudi Sub-Division","Thoothukudi Division","South Coast Circle"],
        "Tiruppur":    ["Tiruppur Sub-Division","Avinashi Division","Tiruppur Circle"],
    }
    FIRST = ["Arjun","Kavitha","Rajan","Priya","Murugan","Lakshmi","Senthil","Anitha",
             "Balasubramaniam","Deepa","Ganesh","Hema","Ilango","Jaya","Karthik","Meena",
             "Nandakumar","Oviya","Prakash","Ramya","Selvam","Thenmozhi","Udhaya",
             "Vijayalakshmi","Yuvaraj","Arunachalam","Bhuvana","Chandran","Dhanabalan",
             "Eswari","Gopalakrishnan","Haripriya","Indhira","Jayakumar","Kiruthika",
             "Logesh","Manikandan","Nandhini","Palanivel","Rajadurai","Supriya",
             "Tamilarasan","Uma","Venkataraman","Wasim","Xavier","Yamuna","Zubair","Abirami"]
    LAST = ["Kumar","Rajan","Devi","Krishnan","Mani","Vel","Murugan","Raja",
            "Balan","Sundaram","Pillai","Pandi","Nathan","Nair","Shankar","Varma","Gounder","Thevar"]
    DESIG_PREFIX = {
        "Junior Engineer":"je","Assistant Engineer":"ae","Divisional Engineer":"de",
        "Executive Engineer":"ee","Superintending Engineer":"se","Chief Engineer":"ce",
    }
    CATEGORIES = ["Mail Not Received","Unable To Send Email","Login Failure","Account Locked","Other"]
    STATUSES = ["Open","Assigned","In Progress","Resolved","Closed"]

    def rd(max_days=120):
        return datetime.utcnow() - timedelta(days=random.randint(0, max_days))

    # Employees
    log.info("Seeding 50 employees …")
    employees, email_set = [], set()
    for i in range(1, 51):
        fname  = FIRST[(i-1) % len(FIRST)]
        lname  = random.choice(LAST)
        desig  = DESIGNATIONS[i % len(DESIGNATIONS)]
        dept   = random.choice(DEPARTMENTS)
        dist   = DISTRICTS[i % len(DISTRICTS)]
        office = random.choice(OFFICES[dist])
        emp = Employee(
            employee_id=f"EMP{i:03d}", name=f"{fname} {lname}",
            designation=desig, department=dept,
            office_location=office, district=dist,
            phone=f"9{random.randint(100000000,999999999)}",
            personal_email=f"{fname.lower()}.{lname.lower()}{i}@gmail.com",
            joined_date=rd(3650).date(), is_active=True,
        )
        db.session.add(emp); db.session.flush(); employees.append(emp)
        prefix = DESIG_PREFIX.get(desig, "emp")
        loc    = dist.lower().replace(" ","_")
        ea     = f"{prefix}_{loc}@tneb.in"
        if ea in email_set: ea = f"{prefix}_{loc}_{i}@tneb.in"
        email_set.add(ea)
        db.session.add(OfficialEmail(
            employee_id_fk=emp.id, email_address=ea,
            designation=desig, office=office, department=dept, district=dist, is_active=True,
        ))
    db.session.commit()

    # Admin users (may already exist from _seed_users)
    admins = User.query.filter(User.role.in_(["admin","superadmin"])).all()

    # Employee login accounts
    for emp in employees[:20]:
        if not User.query.filter_by(username=emp.employee_id).first():
            oe = OfficialEmail.query.filter_by(employee_id_fk=emp.id).first()
            u  = User(username=emp.employee_id,
                      email=oe.email_address if oe else f"{emp.employee_id.lower()}@tneb.in",
                      role="employee", employee_id_fk=emp.id, is_active=True)
            u.set_password("Tneb@1234")
            db.session.add(u)
    db.session.commit()

    # Support tickets
    log.info("Seeding 100 tickets …")
    for i in range(1, 101):
        emp    = random.choice(employees)
        cat    = random.choice(CATEGORIES)
        status = random.choices(STATUSES, weights=[25,15,20,30,10])[0]
        adm    = random.choice(admins) if (admins and status in ("Assigned","In Progress","Resolved","Closed")) else None
        created  = rd(90)
        resolved = created + timedelta(hours=random.randint(2,48)) if status in ("Resolved","Closed") else None
        db.session.add(SupportTicket(
            ticket_id=f"TKT{1000+i}",
            employee_id_fk=emp.id,
            submitter_name=emp.name, submitter_email="",
            category=cat, subject=f"{cat} – {emp.office_location}",
            description=f"{emp.name} ({emp.employee_id}) reported {cat.lower()} at {emp.office_location}.",
            status=status,
            priority=random.choices(["Low","Medium","High","Critical"],weights=[15,45,30,10])[0],
            assigned_to=adm.id if adm else None,
            public_reply=f"Your issue is being handled." if status in ("In Progress","Resolved") else None,
            resolution_notes=f"Resolved by {adm.username}." if status in ("Resolved","Closed") else None,
            created_at=created,
            updated_at=created+timedelta(hours=random.randint(1,24)),
            resolved_at=resolved,
        ))

    # Password reset requests
    for i in range(1, 51):
        emp    = random.choice(employees)
        status = random.choices(["Pending","Approved","Rejected"],weights=[40,50,10])[0]
        adm    = random.choice(admins) if (admins and status!="Pending") else None
        created = rd(60)
        db.session.add(PasswordResetRequest(
            request_id=f"PWD{100+i}", employee_id_fk=emp.id,
            employee_name=emp.name, designation=emp.designation,
            office_location=emp.office_location, phone=emp.phone or "9999999999",
            official_email_submitted=emp.official_email.email_address if emp.official_email else "",
            reason="Forgot password after leave.", status=status,
            approved_by=adm.id if adm else None,
            notes="Verified." if status=="Approved" else None,
            created_at=created,
            resolved_at=created+timedelta(hours=random.randint(1,8)) if status!="Pending" else None,
        ))

    # Email requests
    for i in range(1, 31):
        emp    = random.choice(employees)
        status = random.choices(["Pending","Approved","Rejected"],weights=[40,50,10])[0]
        adm    = random.choice(admins) if (admins and status!="Pending") else None
        created = rd(45)
        db.session.add(EmailRequest(
            request_id=f"EML{200+i}", employee_id_fk=emp.id,
            employee_id_str=emp.employee_id, employee_name=emp.name,
            department=emp.department, designation=emp.designation,
            office_location=emp.office_location,
            phone=emp.phone or "9999999999",
            personal_email=emp.personal_email or "",
            reason="New joinee / email not yet created.",
            status=status,
            approved_by=adm.id if adm else None,
            assigned_email=emp.official_email.email_address if (status=="Approved" and emp.official_email) else None,
            created_at=created,
            resolved_at=created+timedelta(hours=random.randint(2,12)) if status!="Pending" else None,
        ))

    # Seed some notifications
    log.info("Seeding notifications …")
    notif_samples = [
        ("ticket_created",  "New Ticket TKT1001",          "Mail Not Received reported by EMP001", "/admin/tickets"),
        ("pwd_request",     "Password Reset Request PWD101","EMP005 submitted a reset request",    "/admin/password-requests"),
        ("email_request",   "Email Request EML201",         "EMP012 requested an official email",  "/admin/email-requests"),
        ("ticket_updated",  "Ticket TKT1010 Updated",       "Status changed to In Progress",        "/admin/tickets"),
        ("ticket_created",  "New Ticket TKT1050",           "Account Locked – EMP023",             "/admin/tickets"),
    ]
    for type_, title, msg, link in notif_samples:
        db.session.add(Notification(
            user_id=None, type=type_, title=title, message=msg, link=link, is_read=False,
        ))

    db.session.commit()
    log.info("✅ Seed complete.")
    log.info("   Employees  : EMP001–EMP020 / Tneb@1234")
    log.info("   Admins     : admin01–admin09 / Admin@1234")
    log.info("   Superadmin : admin / admin123  |  admin10 / Admin@1234")
