"""
utils.py — Shared helpers: ID generation, notification factory.
"""
import random
import string
from datetime import datetime


def gen_id(prefix: str, model_class, field: str = "request_id") -> str:
    """Generate a unique prefixed ID like TKT1042, PWD201, EML301."""
    from app import db
    for _ in range(20):
        num = random.randint(1000, 9999)
        val = f"{prefix}{num}"
        if not db.session.query(model_class).filter(
            getattr(model_class, field) == val
        ).first():
            return val
    # Fallback: timestamp-based
    return f"{prefix}{int(datetime.utcnow().timestamp()) % 100000}"


def gen_ticket_id() -> str:
    from app.models import SupportTicket
    return gen_id("TKT", SupportTicket, "ticket_id")


def gen_pwd_id() -> str:
    from app.models import PasswordResetRequest
    return gen_id("PWD", PasswordResetRequest, "request_id")


def gen_email_req_id() -> str:
    from app.models import EmailRequest
    return gen_id("EML", EmailRequest, "request_id")


def gen_temp_password() -> str:
    chars = string.ascii_letters + string.digits
    return "Temp@" + "".join(random.choices(chars, k=6))


def notify_admins(type_: str, title: str, message: str, link: str = None):
    """
    Create a Notification row visible to all admin users.
    Call this inside any route that creates/updates something important.
    """
    from app.models import Notification, User, db
    n = Notification(
        user_id=None,   # NULL = all admins see it
        type=type_,
        title=title,
        message=message,
        link=link,
        is_read=False,
    )
    db.session.add(n)
    # Intentionally not committing here — caller commits after their main write
