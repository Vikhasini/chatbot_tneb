"""
public/routes.py
Public-facing pages — no login required.
Home, FAQ, public ticket track, chatbot, forgot-password, email request.
"""
from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import current_user
from app.blueprints.public import public
from app.models import (SupportTicket, Employee, OfficialEmail,
                        PasswordResetRequest, EmailRequest, ChatbotLog, db)
from app.utils import gen_pwd_id, gen_email_req_id, notify_admins
import uuid

# ── Home ──────────────────────────────────────────────────────────────────────

@public.route("/")
def home():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("employee.dashboard"))
    return render_template("public/home.html")

# ── Public chatbot (no login needed) ─────────────────────────────────────────

@public.route("/helpdesk")
def helpdesk():
    return render_template("public/helpdesk.html")

@public.route("/helpdesk/message", methods=["POST"])
def helpdesk_message():
    from app.blueprints.chatbot.engine import detect_intent, build_response
    data         = request.get_json()
    user_message = data.get("message", "").strip()
    session_data = data.get("session_data", {})
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    sid = session.get("pub_chat_sid")
    if not sid:
        sid = str(uuid.uuid4())
        session["pub_chat_sid"] = sid

    db.session.add(ChatbotLog(session_id=sid, user_id=None,
                              message_type="user", message=user_message))

    # Special quick-reply shortcuts
    lower = user_message.lower()
    if lower in ("go to home", "home"):
        resp = {
            "text": "You're back at the main menu. How can I help you?",
            "quick_replies": ["Search Official Email","Track Ticket","Forgot Password",
                              "Request Official Email","FAQs"],
            "session_data": {}, "ticket_created": None,
        }
    elif lower in ("report email issue", "report an issue", "report another issue"):
        resp = {
            "text": ("📋 <strong>Report Email Issue</strong><br><br>"
                     "Please select the issue type:<br><br>"
                     "1️⃣ Mail Not Received<br>2️⃣ Unable To Send Email<br>"
                     "3️⃣ Login Failure<br>4️⃣ Account Locked"),
            "quick_replies": ["Mail Not Received","Unable To Send Email","Login Failure","Account Locked"],
            "session_data": {"state": "collect_issue_category"}, "ticket_created": None,
        }
    else:
        state  = session_data.get("state", "idle")
        intent = state if state not in ("idle", "") else detect_intent(user_message)
        resp   = build_response(intent, user_message, session_data, user_id=None)

    db.session.add(ChatbotLog(session_id=sid, user_id=None,
                              message_type="bot", message=resp["text"],
                              intent=detect_intent(user_message)))
    db.session.commit()
    return jsonify(resp)

# ── Public ticket track ───────────────────────────────────────────────────────

@public.route("/track")
def track():
    return render_template("public/track.html")

@public.route("/track/search")
def track_search():
    tid = request.args.get("ticket_id", "").strip().upper()
    if not tid:
        return jsonify({"error": "No ticket ID"}), 400
    t = SupportTicket.query.filter_by(ticket_id=tid).first()
    if not t:
        return jsonify({"found": False, "message": f"No ticket with ID {tid}"})
    statuses = ["Open","Assigned","In Progress","Resolved","Closed"]
    cur_idx  = statuses.index(t.status) if t.status in statuses else 0
    timeline = [{"status": s, "completed": i <= cur_idx, "active": i == cur_idx,
                 "date": t.created_at.strftime("%d %b") if i == 0 else
                         (t.resolved_at.strftime("%d %b") if t.resolved_at and i >= 3 else None)}
                for i, s in enumerate(statuses)]
    return jsonify({
        "found": True,
        "ticket": {
            "id": t.ticket_id, "category": t.category, "subject": t.subject,
            "description": t.description, "status": t.status, "priority": t.priority,
            "public_reply": t.public_reply,
            "created_at": t.created_at.strftime("%d %b %Y, %I:%M %p"),
            "updated_at": t.updated_at.strftime("%d %b %Y, %I:%M %p"),
            "resolved_at": t.resolved_at.strftime("%d %b %Y, %I:%M %p") if t.resolved_at else None,
            "employee_name": t.employee.name if t.employee else (t.submitter_name or "—"),
        },
        "timeline": timeline,
    })

# ── Public FAQ ────────────────────────────────────────────────────────────────

@public.route("/faq")
def faq():
    return render_template("public/faq.html")

# ── Public forgot password ────────────────────────────────────────────────────

@public.route("/forgot-password", methods=["GET","POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("employee.dashboard"))
    if request.method == "POST":
        emp_id   = request.form.get("employee_id","").strip().upper()
        phone    = request.form.get("phone","").strip()
        email    = request.form.get("official_email","").strip().lower()
        reason   = request.form.get("reason","").strip()
        errors   = []
        if not emp_id:  errors.append("Employee ID is required.")
        if not phone:   errors.append("Mobile number is required.")
        if not email:   errors.append("Official email is required.")
        if not reason:  errors.append("Reason is required.")
        if errors:
            for e in errors: flash(e, "danger")
            return render_template("public/forgot_password.html", form_data=request.form)

        emp = Employee.query.filter_by(employee_id=emp_id, is_active=True).first()
        if not emp:
            flash("No active employee found with that Employee ID.", "danger")
            return render_template("public/forgot_password.html", form_data=request.form)
        sub_ph = "".join(filter(str.isdigit, phone))
        sto_ph = "".join(filter(str.isdigit, emp.phone or ""))
        if sub_ph != sto_ph:
            flash("Mobile number does not match our records.", "danger")
            return render_template("public/forgot_password.html", form_data=request.form)
        oe = OfficialEmail.query.filter_by(employee_id_fk=emp.id, is_active=True).first()
        if not oe or email != oe.email_address.lower():
            flash("Official email does not match our records.", "danger")
            return render_template("public/forgot_password.html", form_data=request.form)
        existing = PasswordResetRequest.query.filter_by(
            employee_id_fk=emp.id, status="Pending").first()
        if existing:
            flash(f"You already have a pending request ({existing.request_id}).", "warning")
            return render_template("public/forgot_password.html", form_data=request.form)

        pr = PasswordResetRequest(
            request_id=gen_pwd_id(), employee_id_fk=emp.id,
            employee_name=emp.name, designation=emp.designation,
            office_location=emp.office_location, phone=phone,
            official_email_submitted=email, reason=reason, status="Pending",
        )
        db.session.add(pr)
        notify_admins("pwd_request",
                      f"Password Reset Request {pr.request_id}",
                      f"{emp.name} ({emp.employee_id}) submitted a password reset request.",
                      "/admin/password-requests")
        db.session.commit()
        return render_template("public/forgot_password_success.html",
                               request_id=pr.request_id, employee_name=emp.name)
    return render_template("public/forgot_password.html", form_data={})

# ── Public email request ──────────────────────────────────────────────────────

@public.route("/request-email", methods=["GET","POST"])
def request_email():
    if request.method == "POST":
        emp_id    = request.form.get("employee_id","").strip().upper()
        name      = request.form.get("name","").strip()
        dept      = request.form.get("department","").strip()
        desig     = request.form.get("designation","").strip()
        office    = request.form.get("office_location","").strip()
        phone     = request.form.get("phone","").strip()
        per_email = request.form.get("personal_email","").strip()
        reason    = request.form.get("reason","").strip()

        errors = []
        if not emp_id: errors.append("Employee ID is required.")
        if not name:   errors.append("Full name is required.")
        if not dept:   errors.append("Department is required.")
        if not desig:  errors.append("Designation is required.")
        if not office: errors.append("Office Location is required.")
        if errors:
            for e in errors: flash(e, "danger")
            return render_template("public/request_email.html", form_data=request.form)

        # Find employee record if exists
        emp_rec = Employee.query.filter_by(employee_id=emp_id).first()

        er = EmailRequest(
            request_id=gen_email_req_id(),
            employee_id_fk=emp_rec.id if emp_rec else None,
            employee_id_str=emp_id, employee_name=name,
            department=dept, designation=desig, office_location=office,
            phone=phone, personal_email=per_email, reason=reason, status="Pending",
        )
        db.session.add(er)
        notify_admins("email_request",
                      f"Email Request {er.request_id}",
                      f"{name} ({emp_id}) requested an official email ID.",
                      "/admin/email-requests")
        db.session.commit()
        return render_template("public/request_email_success.html",
                               request_id=er.request_id, name=name)
    return render_template("public/request_email.html", form_data={})
