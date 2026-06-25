from flask import jsonify, request
from flask_login import login_required, current_user
from app.blueprints.notifications import notifications
from app.models import Notification, db


@notifications.route("/unread-count")
@login_required
def unread_count():
    if not current_user.is_admin:
        return jsonify({"count": 0})
    count = Notification.query.filter(
        (Notification.user_id == None) | (Notification.user_id == current_user.id),
        Notification.is_read == False
    ).count()
    return jsonify({"count": count})


@notifications.route("/list")
@login_required
def list_notifications():
    if not current_user.is_admin:
        return jsonify({"notifications": []})
    items = Notification.query.filter(
        (Notification.user_id == None) | (Notification.user_id == current_user.id)
    ).order_by(Notification.created_at.desc()).limit(30).all()
    return jsonify({"notifications": [
        {"id": n.id, "type": n.type, "title": n.title, "message": n.message,
         "link": n.link, "is_read": n.is_read,
         "created_at": n.created_at.strftime("%d %b %Y, %I:%M %p")}
        for n in items
    ]})


@notifications.route("/mark-read", methods=["POST"])
@login_required
def mark_read():
    data = request.get_json()
    nids = data.get("ids", [])
    if nids:
        Notification.query.filter(Notification.id.in_(nids)).update(
            {"is_read": True}, synchronize_session=False)
    else:
        # Mark all
        Notification.query.filter(
            (Notification.user_id == None) | (Notification.user_id == current_user.id)
        ).update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"success": True})
