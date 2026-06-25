"""
models/__init__.py
TNEB Digital Helpdesk & Official Email Support Portal
PostgreSQL-compatible. All relationships explicitly defined.
"""
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


# ── Employee ──────────────────────────────────────────────────────────────────

class Employee(db.Model):
    __tablename__ = "employees"

    id              = db.Column(db.Integer, primary_key=True)
    employee_id     = db.Column(db.String(20),  unique=True, nullable=False, index=True)
    name            = db.Column(db.String(120), nullable=False)
    designation     = db.Column(db.String(100), nullable=False)
    department      = db.Column(db.String(100), nullable=False)
    office_location = db.Column(db.String(100), nullable=False)
    district        = db.Column(db.String(60),  nullable=False)
    phone           = db.Column(db.String(15))
    personal_email  = db.Column(db.String(120))
    joined_date     = db.Column(db.Date)
    is_active       = db.Column(db.Boolean, default=True, nullable=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    official_email    = db.relationship("OfficialEmail", backref="employee", uselist=False)
    tickets           = db.relationship("SupportTicket", backref="employee", lazy="dynamic",
                                        foreign_keys="SupportTicket.employee_id_fk")
    password_requests = db.relationship("PasswordResetRequest", backref="employee", lazy="dynamic",
                                        foreign_keys="PasswordResetRequest.employee_id_fk")
    email_requests    = db.relationship("EmailRequest", backref="employee", lazy="dynamic",
                                        foreign_keys="EmailRequest.employee_id_fk")

    def __repr__(self):
        return f"<Employee {self.employee_id} — {self.name}>"


# ── OfficialEmail ─────────────────────────────────────────────────────────────

class OfficialEmail(db.Model):
    __tablename__ = "official_emails"

    id              = db.Column(db.Integer, primary_key=True)
    employee_id_fk  = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"),
                                 nullable=False)
    email_address   = db.Column(db.String(150), unique=True, nullable=False, index=True)
    designation     = db.Column(db.String(100), nullable=False)
    office          = db.Column(db.String(100), nullable=False)
    department      = db.Column(db.String(100), nullable=False)
    district        = db.Column(db.String(60),  nullable=False)
    is_active       = db.Column(db.Boolean, default=True, nullable=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_updated    = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<OfficialEmail {self.email_address}>"


# ── User ──────────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(80),  unique=True, nullable=False, index=True)
    email           = db.Column(db.String(120), unique=True, nullable=False)
    password_hash   = db.Column(db.String(256), nullable=False)
    # Roles: employee | admin | superadmin
    role            = db.Column(db.String(20),  nullable=False, default="employee")
    employee_id_fk  = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"),
                                 nullable=True)
    is_active       = db.Column(db.Boolean, default=True, nullable=False)
    last_login      = db.Column(db.DateTime)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    employee = db.relationship("Employee", backref="user", foreign_keys=[employee_id_fk])
    assigned_tickets = db.relationship(
        "SupportTicket", backref="assigned_admin",
        foreign_keys="SupportTicket.assigned_to", lazy="dynamic",
    )

    def set_password(self, p: str):
        self.password_hash = generate_password_hash(p)

    def check_password(self, p: str) -> bool:
        return check_password_hash(self.password_hash, p)

    @property
    def is_admin(self) -> bool:
        return self.role in ("admin", "superadmin")

    def __repr__(self):
        return f"<User {self.username} [{self.role}]>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ── SupportTicket ─────────────────────────────────────────────────────────────

class SupportTicket(db.Model):
    __tablename__ = "support_tickets"

    id               = db.Column(db.Integer, primary_key=True)
    ticket_id        = db.Column(db.String(20), unique=True, nullable=False, index=True)
    # nullable FK so public users (no employee record) can also raise tickets
    employee_id_fk   = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"),
                                  nullable=True)
    # For public/anonymous submissions
    submitter_name   = db.Column(db.String(120))
    submitter_email  = db.Column(db.String(150))
    submitter_phone  = db.Column(db.String(15))

    category         = db.Column(db.String(60),  nullable=False)
    subject          = db.Column(db.String(200), nullable=False)
    description      = db.Column(db.Text, nullable=False)
    # Status: Open | Assigned | In Progress | Pending Employee | Resolved | Closed
    status           = db.Column(db.String(30),  nullable=False, default="Open")
    # Priority: Low | Medium | High | Critical
    priority         = db.Column(db.String(20),  nullable=False, default="Medium")
    assigned_to      = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
                                  nullable=True)
    # Visible to the submitter
    public_reply     = db.Column(db.Text)
    # Visible to admins only
    internal_notes   = db.Column(db.Text)
    # Legacy field kept for compatibility
    resolution_notes = db.Column(db.Text)

    created_at       = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at       = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_at      = db.Column(db.DateTime)

    def __repr__(self):
        return f"<Ticket {self.ticket_id} [{self.status}]>"


# ── PasswordResetRequest ──────────────────────────────────────────────────────

class PasswordResetRequest(db.Model):
    __tablename__ = "password_reset_requests"

    id                       = db.Column(db.Integer, primary_key=True)
    request_id               = db.Column(db.String(20), unique=True, nullable=False, index=True)
    employee_id_fk           = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"),
                                          nullable=False)
    employee_name            = db.Column(db.String(120), nullable=False)
    designation              = db.Column(db.String(100), nullable=False)
    office_location          = db.Column(db.String(100), nullable=False)
    phone                    = db.Column(db.String(15),  nullable=False)
    official_email_submitted = db.Column(db.String(150))
    reason                   = db.Column(db.Text)
    # Status: Pending | Approved | Rejected
    status                   = db.Column(db.String(30), nullable=False, default="Pending")
    approved_by              = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
                                          nullable=True)
    rejection_reason         = db.Column(db.Text)
    temp_password_plain      = db.Column(db.String(30))
    notes                    = db.Column(db.Text)
    created_at               = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_at              = db.Column(db.DateTime)

    approver = db.relationship("User", foreign_keys=[approved_by])

    def __repr__(self):
        return f"<PasswordResetRequest {self.request_id} [{self.status}]>"


# ── EmailRequest ──────────────────────────────────────────────────────────────
# New: Public or employee can request an official email ID to be created

class EmailRequest(db.Model):
    __tablename__ = "email_requests"

    id              = db.Column(db.Integer, primary_key=True)
    request_id      = db.Column(db.String(20), unique=True, nullable=False, index=True)
    # Link to employee if they exist; nullable for new joiners
    employee_id_fk  = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"),
                                 nullable=True)
    # Submitter details (captured at submit time)
    employee_id_str = db.Column(db.String(20), nullable=False)   # typed employee ID
    employee_name   = db.Column(db.String(120), nullable=False)
    department      = db.Column(db.String(100), nullable=False)
    designation     = db.Column(db.String(100), nullable=False)
    office_location = db.Column(db.String(100), nullable=False)
    phone           = db.Column(db.String(15))
    personal_email  = db.Column(db.String(150))
    reason          = db.Column(db.Text)
    # Status: Pending | Approved | Rejected
    status          = db.Column(db.String(30), nullable=False, default="Pending")
    approved_by     = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
                                 nullable=True)
    # Admin fills this on approval — the actual email created
    assigned_email  = db.Column(db.String(150))
    rejection_reason = db.Column(db.Text)
    admin_remarks   = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_at     = db.Column(db.DateTime)

    approver = db.relationship("User", foreign_keys=[approved_by])

    def __repr__(self):
        return f"<EmailRequest {self.request_id} [{self.status}]>"


# ── Notification ──────────────────────────────────────────────────────────────

class Notification(db.Model):
    __tablename__ = "notifications"

    id          = db.Column(db.Integer, primary_key=True)
    # Who receives this notification (admin user id); NULL = broadcast to all admins
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                             nullable=True)
    # Type: ticket_created | ticket_updated | pwd_request | email_request | general
    type        = db.Column(db.String(40), nullable=False)
    title       = db.Column(db.String(200), nullable=False)
    message     = db.Column(db.Text, nullable=False)
    # Link to the relevant record (e.g. /admin/tickets or /admin/password-requests)
    link        = db.Column(db.String(200))
    is_read     = db.Column(db.Boolean, default=False, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Notification {self.id} [{self.type}] read={self.is_read}>"


# ── ChatbotLog ────────────────────────────────────────────────────────────────

class ChatbotLog(db.Model):
    __tablename__ = "chatbot_logs"

    id           = db.Column(db.Integer, primary_key=True)
    session_id   = db.Column(db.String(60), nullable=False, index=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
                              nullable=True)
    message_type = db.Column(db.String(10), nullable=False)   # user | bot
    message      = db.Column(db.Text, nullable=False)
    intent       = db.Column(db.String(60))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ChatbotLog {self.session_id} [{self.message_type}]>"
