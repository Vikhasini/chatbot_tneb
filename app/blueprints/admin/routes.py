from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from app.blueprints.admin import admin
from app.models import (SupportTicket, Employee, User, Notification,
                        PasswordResetRequest, EmailRequest, OfficialEmail, db)
from app.utils import gen_temp_password, notify_admins
from datetime import datetime, timedelta
from sqlalchemy import func
import random, string


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Admin access required.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def _unread_count():
    return Notification.query.filter(
        (Notification.user_id == None) | (Notification.user_id == current_user.id),
        Notification.is_read == False
    ).count()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@admin.route("/dashboard")
@login_required
@admin_required
def dashboard():
    stats = {
        "total_employees":  Employee.query.count(),
        "total_tickets":    SupportTicket.query.count(),
        "open_tickets":     SupportTicket.query.filter(SupportTicket.status.in_(["Open","Assigned","In Progress"])).count(),
        "resolved_tickets": SupportTicket.query.filter(SupportTicket.status.in_(["Resolved","Closed"])).count(),
        "pwd_pending":      PasswordResetRequest.query.filter_by(status="Pending").count(),
        "email_pending":    EmailRequest.query.filter_by(status="Pending").count(),
        "unread_notifs":    _unread_count(),
    }
    recent_tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).limit(8).all()
    recent_notifs  = Notification.query.filter(
        (Notification.user_id == None) | (Notification.user_id == current_user.id)
    ).order_by(Notification.created_at.desc()).limit(10).all()

    # Charts
    status_data = db.session.query(SupportTicket.status, func.count(SupportTicket.id))\
                            .group_by(SupportTicket.status).all()
    monthly = []
    for i in range(5, -1, -1):
        ms = datetime.utcnow().replace(day=1) - timedelta(days=30*i)
        me = (datetime.utcnow().replace(day=1) - timedelta(days=30*(i-1))) if i>0 else datetime.utcnow()
        monthly.append({"month": ms.strftime("%b %Y"),
                        "count": SupportTicket.query.filter(
                            SupportTicket.created_at >= ms,
                            SupportTicket.created_at < me).count()})
    cat_data = db.session.query(SupportTicket.category, func.count(SupportTicket.id))\
                         .group_by(SupportTicket.category).all()

    return render_template("admin/dashboard.html",
                           stats=stats, recent_tickets=recent_tickets,
                           recent_notifs=recent_notifs,
                           status_data=status_data, monthly_data=monthly, cat_data=cat_data)


# ── Notifications ─────────────────────────────────────────────────────────────

@admin.route("/notifications")
@login_required
@admin_required
def notifications_page():
    page  = request.args.get("page", 1, type=int)
    notifs = Notification.query.filter(
        (Notification.user_id == None) | (Notification.user_id == current_user.id)
    ).order_by(Notification.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    # Mark all as read
    Notification.query.filter(
        (Notification.user_id == None) | (Notification.user_id == current_user.id),
        Notification.is_read == False
    ).update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return render_template("admin/notifications.html", notifs=notifs, unread=0)


# ── Tickets ───────────────────────────────────────────────────────────────────

@admin.route("/tickets")
@login_required
@admin_required
def ticket_list():
    status_filter = request.args.get("status","")
    search        = request.args.get("search","")
    page          = request.args.get("page", 1, type=int)
    query = SupportTicket.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if search:
        query = query.outerjoin(Employee, SupportTicket.employee_id_fk == Employee.id).filter(
            SupportTicket.ticket_id.ilike(f"%{search}%") |
            Employee.name.ilike(f"%{search}%") |
            SupportTicket.submitter_name.ilike(f"%{search}%") |
            SupportTicket.category.ilike(f"%{search}%")
        )
    tickets_pag = query.order_by(SupportTicket.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False)
    admins = User.query.filter(User.role.in_(["admin","superadmin"])).all()
    return render_template("admin/tickets.html",
                           tickets=tickets_pag, admins=admins,
                           status_filter=status_filter, search=search,
                           unread=_unread_count())


@admin.route("/tickets/<int:tid>/update", methods=["POST"])
@login_required
@admin_required
def update_ticket(tid):
    t = db.session.get(SupportTicket, tid)
    if not t: return jsonify({"error": "Not found"}), 404
    data = request.get_json()
    changed = []
    if "status" in data:
        t.status = data["status"]
        if data["status"] in ("Resolved","Closed"):
            t.resolved_at = datetime.utcnow()
        changed.append(f"Status → {data['status']}")
    if "assigned_to" in data and data["assigned_to"]:
        t.assigned_to = int(data["assigned_to"])
        if t.status == "Open": t.status = "Assigned"
    if "priority" in data:
        t.priority = data["priority"]
    if "public_reply" in data:
        t.public_reply = data["public_reply"]
    if "internal_notes" in data:
        t.internal_notes = data["internal_notes"]
    if "resolution_notes" in data:
        t.resolution_notes = data["resolution_notes"]
    t.updated_at = datetime.utcnow()
    if changed:
        notify_admins("ticket_updated", f"Ticket {t.ticket_id} Updated",
                      f"{', '.join(changed)} by {current_user.username}",
                      "/admin/tickets")
    db.session.commit()
    return jsonify({"success": True, "ticket_id": t.ticket_id, "status": t.status})


# ── Password Requests ─────────────────────────────────────────────────────────

@admin.route("/password-requests")
@login_required
@admin_required
def password_requests():
    sf   = request.args.get("status","")
    page = request.args.get("page", 1, type=int)
    q = PasswordResetRequest.query
    if sf: q = q.filter_by(status=sf)
    pag = q.order_by(PasswordResetRequest.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template("admin/password_requests.html",
                           requests=pag, status_filter=sf,
                           pending_count=PasswordResetRequest.query.filter_by(status="Pending").count(),
                           approved_count=PasswordResetRequest.query.filter_by(status="Approved").count(),
                           rejected_count=PasswordResetRequest.query.filter_by(status="Rejected").count(),
                           unread=_unread_count())


@admin.route("/password-requests/<int:rid>/action", methods=["POST"])
@login_required
@admin_required
def pwd_request_action(rid):
    pr     = db.session.get(PasswordResetRequest, rid)
    if not pr: return jsonify({"error": "Not found"}), 404
    data   = request.get_json()
    action = data.get("action")
    if action == "approve":
        tmp = gen_temp_password()
        u   = User.query.filter_by(employee_id_fk=pr.employee_id_fk).first()
        if u: u.set_password(tmp)
        pr.temp_password_plain = tmp
        pr.status = "Approved"; pr.approved_by = current_user.id
        pr.notes  = data.get("notes",""); pr.resolved_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"success": True, "status": "Approved",
                        "temp_password": tmp, "employee_name": pr.employee_name})
    elif action == "reject":
        reason = data.get("rejection_reason","").strip()
        if not reason: return jsonify({"error": "Rejection reason required."}), 400
        pr.status = "Rejected"; pr.approved_by = current_user.id
        pr.rejection_reason = reason; pr.resolved_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"success": True, "status": "Rejected"})
    return jsonify({"error": "Invalid action"}), 400


# ── Email Requests ────────────────────────────────────────────────────────────

@admin.route("/email-requests")
@login_required
@admin_required
def email_requests():
    sf   = request.args.get("status","")
    page = request.args.get("page", 1, type=int)
    q = EmailRequest.query
    if sf: q = q.filter_by(status=sf)
    pag = q.order_by(EmailRequest.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template("admin/email_requests.html",
                           requests=pag, status_filter=sf,
                           pending_count=EmailRequest.query.filter_by(status="Pending").count(),
                           approved_count=EmailRequest.query.filter_by(status="Approved").count(),
                           rejected_count=EmailRequest.query.filter_by(status="Rejected").count(),
                           unread=_unread_count())


@admin.route("/email-requests/<int:rid>/action", methods=["POST"])
@login_required
@admin_required
def email_request_action(rid):
    er     = db.session.get(EmailRequest, rid)
    if not er: return jsonify({"error": "Not found"}), 404
    data   = request.get_json()
    action = data.get("action")
    if action == "approve":
        assigned = data.get("assigned_email","").strip()
        if not assigned: return jsonify({"error": "Assigned email is required."}), 400
        er.status = "Approved"; er.approved_by = current_user.id
        er.assigned_email = assigned; er.admin_remarks = data.get("remarks","")
        er.resolved_at = datetime.utcnow()
        # Create OfficialEmail record if employee exists
        if er.employee_id_fk:
            existing = OfficialEmail.query.filter_by(employee_id_fk=er.employee_id_fk).first()
            if not existing:
                db.session.add(OfficialEmail(
                    employee_id_fk=er.employee_id_fk,
                    email_address=assigned, designation=er.designation,
                    office=er.office_location, department=er.department,
                    district="",  is_active=True,
                ))
        db.session.commit()
        return jsonify({"success": True, "status": "Approved", "assigned_email": assigned})
    elif action == "reject":
        reason = data.get("rejection_reason","").strip()
        if not reason: return jsonify({"error": "Rejection reason required."}), 400
        er.status = "Rejected"; er.approved_by = current_user.id
        er.rejection_reason = reason; er.admin_remarks = data.get("remarks","")
        er.resolved_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"success": True, "status": "Rejected"})
    return jsonify({"error": "Invalid action"}), 400


# ── Employees ─────────────────────────────────────────────────────────────────

@admin.route("/employees")
@login_required
@admin_required
def employees():
    search = request.args.get("search","")
    page   = request.args.get("page", 1, type=int)
    q = Employee.query
    if search:
        q = q.filter(Employee.name.ilike(f"%{search}%") |
                     Employee.employee_id.ilike(f"%{search}%") |
                     Employee.office_location.ilike(f"%{search}%"))
    pag = q.order_by(Employee.name).paginate(page=page, per_page=20, error_out=False)
    return render_template("admin/employees.html", employees=pag,
                           search=search, unread=_unread_count())
