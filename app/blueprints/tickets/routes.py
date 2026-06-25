from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.blueprints.tickets import tickets
from app.models import SupportTicket, db


@tickets.route("/track")
@login_required
def track():
    return render_template("tickets/track.html")


@tickets.route("/search")
@login_required
def search():
    tid = request.args.get("ticket_id","").strip().upper()
    if not tid:
        return jsonify({"error": "No ticket ID provided"}), 400
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
            "assigned_to": t.assigned_admin.username if t.assigned_admin else None,
            "resolution_notes": t.resolution_notes,
            "employee_name": t.employee.name if t.employee else (t.submitter_name or "—"),
            "employee_office": t.employee.office_location if t.employee else "—",
            "employee_designation": t.employee.designation if t.employee else "—",
        },
        "timeline": timeline,
    })
