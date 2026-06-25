from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.blueprints.employee import employee
from app.models import SupportTicket, db
from app.utils import gen_ticket_id, notify_admins
from datetime import datetime


@employee.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))
    emp = current_user.employee
    recent_tickets = []
    if emp:
        recent_tickets = SupportTicket.query.filter_by(employee_id_fk=emp.id)\
                         .order_by(SupportTicket.created_at.desc()).limit(5).all()
    announcements = [
        {"title": "Email System Maintenance",
         "date": "20 Jun 2025",
         "body": "Scheduled maintenance on TNEB email servers on 22 Jun 2025 from 11 PM to 2 AM.",
         "type": "warning"},
        {"title": "New Password Policy Effective July 2025",
         "date": "15 Jun 2025",
         "body": "All employees must update passwords to comply with the new 12-character minimum policy.",
         "type": "info"},
        {"title": "Helpdesk Portal Upgraded",
         "date": "01 Jun 2025",
         "body": "TNEB Digital Helpdesk upgraded with AI chatbot support and faster ticket resolution.",
         "type": "success"},
    ]
    return render_template("employee/dashboard.html",
                           employee=emp, recent_tickets=recent_tickets,
                           announcements=announcements)


@employee.route("/raise-ticket", methods=["GET","POST"])
@login_required
def raise_ticket():
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))
    emp = current_user.employee
    if request.method == "POST":
        cat   = request.form.get("category","").strip()
        subj  = request.form.get("subject","").strip()
        desc  = request.form.get("description","").strip()
        prior = request.form.get("priority","Medium")
        if not cat or not subj or not desc:
            flash("Category, subject and description are required.", "danger")
            return render_template("employee/raise_ticket.html", employee=emp)
        t = SupportTicket(
            ticket_id=gen_ticket_id(),
            employee_id_fk=emp.id if emp else None,
            submitter_name=emp.name if emp else current_user.username,
            submitter_email="",
            category=cat, subject=subj, description=desc,
            priority=prior, status="Open",
        )
        db.session.add(t)
        notify_admins("ticket_created", f"New Ticket {t.ticket_id}",
                      f"{cat} reported by {emp.name if emp else current_user.username}.",
                      "/admin/tickets")
        db.session.commit()
        flash(f"Ticket {t.ticket_id} raised successfully.", "success")
        return redirect(url_for("employee.ticket_history"))
    return render_template("employee/raise_ticket.html", employee=emp)


@employee.route("/tickets")
@login_required
def ticket_history():
    if current_user.is_admin:
        return redirect(url_for("admin.ticket_list"))
    emp = current_user.employee
    page = request.args.get("page", 1, type=int)
    if emp:
        pag = SupportTicket.query.filter_by(employee_id_fk=emp.id)\
              .order_by(SupportTicket.created_at.desc())\
              .paginate(page=page, per_page=10, error_out=False)
    else:
        pag = SupportTicket.query.filter_by(id=0).paginate(page=1, per_page=10)
    return render_template("employee/ticket_history.html", tickets=pag, employee=emp)
