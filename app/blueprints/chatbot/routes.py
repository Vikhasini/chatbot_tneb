from flask import render_template, request, jsonify, session
from flask_login import login_required, current_user
from app.blueprints.chatbot import chatbot
from app.blueprints.chatbot.engine import detect_intent, build_response
from app.models import ChatbotLog, db
import uuid


@chatbot.route("/support")
@login_required
def support():
    return render_template("chatbot/support.html")


@chatbot.route("/message", methods=["POST"])
@login_required
def message():
    data         = request.get_json()
    user_message = data.get("message", "").strip()
    session_data = data.get("session_data", {})
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    sid = session.get("chat_session_id")
    if not sid:
        sid = str(uuid.uuid4())
        session["chat_session_id"] = sid

    db.session.add(ChatbotLog(session_id=sid, user_id=current_user.id,
                              message_type="user", message=user_message))
    lower = user_message.lower()
    if lower in ("go to home", "home"):
        resp = {
            "text": "You're back at the main menu! How can I help you?",
            "quick_replies": ["Search Official Email","Report Email Issue",
                              "Track Ticket","Forgot Password"],
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
        intent = state if state not in ("idle","") else detect_intent(user_message)
        resp   = build_response(intent, user_message, session_data, current_user.id)

    db.session.add(ChatbotLog(session_id=sid, user_id=current_user.id,
                              message_type="bot", message=resp["text"],
                              intent=detect_intent(user_message)))
    db.session.commit()
    return jsonify(resp)
