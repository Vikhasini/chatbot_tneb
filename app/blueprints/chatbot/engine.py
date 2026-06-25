"""
Rule-based chatbot engine for TNEB Email Support Portal.
Password recovery now redirects to the public /auth/forgot-password page.
"""
import re
from app.models import OfficialEmail, Employee, SupportTicket, PasswordResetRequest, ChatbotLog, db
from datetime import datetime
import random


def generate_ticket_id():
    num = random.randint(1000, 9999)
    return f'TKT{num}'


def detect_intent(message: str) -> str:
    msg = message.lower().strip()

    if re.search(r'\b(hi|hello|hey|good morning|good afternoon|namaste|vanakkam)\b', msg):
        return 'greeting'

    if re.search(r'tkt\d+', msg, re.IGNORECASE):
        return 'track_ticket_direct'
    if re.search(r'\b(track ticket|ticket status|check ticket|my ticket)\b', msg):
        return 'track_ticket'

    if re.search(r'\b(find email|search email|official email|email of|email id|get email)\b', msg):
        return 'search_email'
    if re.search(r'\b(assistant engineer|executive engineer|superintending engineer|'
                 r'divisional engineer|junior engineer|chief engineer|ae |ee |se |de |je |ce )\b', msg):
        return 'search_email_direct'

    # Password-related — now redirect to dedicated page
    if re.search(r'\b(forgot password|reset password|change password|password expired|'
                 r'password help|password recovery|recover password|lost password)\b', msg):
        return 'forgot_password'

    if re.search(r'\b(mail not received|not receiving|emails not coming|inbox empty)\b', msg):
        return 'mail_not_received'
    if re.search(r'\b(cannot send|cant send|unable to send|sending fail|outbox stuck)\b', msg):
        return 'unable_to_send'
    if re.search(r'\b(login fail|cannot login|unable to login|login error|sign in fail)\b', msg):
        return 'login_failure'
    if re.search(r'\b(account locked|locked out|account block|suspended)\b', msg):
        return 'account_locked'

    if re.search(r'\b(help|what can you do|options|menu|services)\b', msg):
        return 'help'

    if re.search(r'\b(thank|thanks|ok|okay|got it|bye|goodbye)\b', msg):
        return 'thanks'

    return 'unknown'


def build_response(intent: str, message: str, session_data: dict, user_id: int = None):
    response = {
        'text': '',
        'quick_replies': [],
        'session_data': session_data.copy(),
        'ticket_created': None,
    }

    state = session_data.get('state', 'idle')

    # ── State machine for issue reporting ─────────────────────────────────────

    if state == 'collect_issue_category':
        categories = {
            '1': 'Mail Not Received',
            '2': 'Unable To Send Email',
            '3': 'Login Failure',
            '4': 'Account Locked',
            'mail not received': 'Mail Not Received',
            'unable to send email': 'Unable To Send Email',
            'login failure': 'Login Failure',
            'account locked': 'Account Locked',
        }
        cat = categories.get(message.strip().lower())
        if cat:
            response['session_data']['issue_category'] = cat
            response['session_data']['state'] = 'collect_issue_desc'
            response['text'] = (
                f"📌 Category: <strong>{cat}</strong><br><br>"
                "Please describe the issue in detail (when it started, any error messages, etc.):"
            )
        else:
            response['text'] = (
                "Please select a valid option:<br>"
                "1️⃣ Mail Not Received<br>"
                "2️⃣ Unable To Send Email<br>"
                "3️⃣ Login Failure<br>"
                "4️⃣ Account Locked"
            )
            response['quick_replies'] = ['Mail Not Received', 'Unable To Send Email',
                                          'Login Failure', 'Account Locked']
        return response

    if state == 'collect_issue_desc':
        response['session_data']['issue_desc'] = message
        response['session_data']['state'] = 'collect_issue_empid'
        response['text'] = "Please provide your <strong>Employee ID</strong> to raise the ticket:"
        return response

    if state == 'collect_issue_empid':
        emp = Employee.query.filter_by(employee_id=message.strip().upper()).first()
        if emp:
            cat  = response['session_data'].get('issue_category', 'Other')
            desc = response['session_data'].get('issue_desc', 'No description provided.')

            ticket_id = generate_ticket_id()
            while SupportTicket.query.filter_by(ticket_id=ticket_id).first():
                ticket_id = generate_ticket_id()

            ticket = SupportTicket(
                ticket_id=ticket_id,
                employee_id_fk=emp.id,
                category=cat,
                subject=f'{cat} - {emp.office_location}',
                description=desc,
                status='Pending',
                priority='High' if cat == 'Account Locked' else 'Medium',
            )
            db.session.add(ticket)
            db.session.commit()

            response['session_data']['state'] = 'idle'
            response['text'] = (
                f"🎫 <strong>Support Ticket Created!</strong><br><br>"
                f"🔖 Ticket ID: <code>{ticket_id}</code><br>"
                f"📁 Category: {cat}<br>"
                f"👤 Employee: {emp.name}<br>"
                f"🏢 Office: {emp.office_location}<br>"
                f"⚡ Priority: {ticket.priority}<br>"
                f"📋 Status: <span class='badge-pending'>Pending</span><br><br>"
                f"Our support team will respond within <strong>2–4 working hours</strong>. "
                f"Use <code>Track {ticket_id}</code> to check status."
            )
            response['ticket_created'] = {'id': ticket_id, 'category': cat, 'status': 'Pending'}
            response['quick_replies'] = [f'Track {ticket_id}', 'Report another issue', 'Go to home']
        else:
            response['text'] = "❌ Employee ID not found. Please enter a valid Employee ID:"
        return response

    # ── Intent responses ──────────────────────────────────────────────────────

    if intent == 'greeting':
        response['text'] = (
            "👋 Vanakkam! Welcome to <strong>TNEB Email Support Portal</strong>.<br><br>"
            "I'm your virtual helpdesk assistant. How can I help you today?"
        )
        response['quick_replies'] = [
            'Search Official Email', 'Report Email Issue', 'Track Ticket', 'Forgot Password'
        ]
        return response

    if intent == 'help':
        response['text'] = (
            "🛠️ <strong>Available Services:</strong><br><br>"
            "📧 <strong>Search Official Email</strong> — Find any TNEB official email ID<br>"
            "📬 <strong>Mail Not Received</strong> — Report missing emails<br>"
            "📤 <strong>Unable To Send</strong> — Report outgoing email issues<br>"
            "🔐 <strong>Login Failure</strong> — Fix login problems<br>"
            "🔒 <strong>Account Locked</strong> — Unlock your email account<br>"
            "🎫 <strong>Track Ticket</strong> — Check your support ticket status<br>"
            "🔑 <strong>Forgot Password</strong> — Reset your portal password<br>"
        )
        response['quick_replies'] = [
            'Search Official Email', 'Report Email Issue', 'Track Ticket', 'Forgot Password'
        ]
        return response

    if intent == 'forgot_password':
        # Redirect to the dedicated public page — do NOT collect details in chat
        response['text'] = (
            "🔑 <strong>Password Reset</strong><br><br>"
            "To reset your password, please use the dedicated <strong>Forgot Password</strong> page "
            "which is accessible directly from the login screen — no login required.<br><br>"
            "You will need to provide:<br>"
            "• Your Employee ID<br>"
            "• Registered Mobile Number<br>"
            "• Official Email Address<br>"
            "• Reason for reset<br><br>"
            "An administrator will verify your identity and set a temporary password within "
            "<strong>4 working hours</strong>.<br><br>"
            "<a href='/auth/forgot-password' "
            "style='display:inline-flex;align-items:center;gap:6px;padding:7px 16px;"
            "background:#004A99;color:#fff;border-radius:20px;text-decoration:none;"
            "font-size:13px;font-weight:600;margin-top:4px'>"
            "<i class='bi bi-key-fill'></i> Go to Forgot Password Page</a>"
        )
        response['quick_replies'] = ['Report Email Issue', 'Track Ticket', 'Search Official Email']
        return response

    if intent in ('track_ticket_direct', 'track_ticket'):
        match = re.search(r'tkt\d+', message, re.IGNORECASE)
        if match:
            tid    = match.group(0).upper()
            ticket = SupportTicket.query.filter_by(ticket_id=tid).first()
            if ticket:
                emp        = ticket.employee
                admin_name = ticket.assigned_admin.username if ticket.assigned_admin else 'Not yet assigned'
                status_icon = {
                    'Pending': '🟡', 'Assigned': '🔵', 'In Progress': '🟠',
                    'Resolved': '🟢', 'Closed': '⚫',
                }.get(ticket.status, '⚪')
                response['text'] = (
                    f"🎫 <strong>Ticket Details</strong><br><br>"
                    f"🔖 Ticket ID: <code>{ticket.ticket_id}</code><br>"
                    f"📁 Category: {ticket.category}<br>"
                    f"📝 Subject: {ticket.subject}<br>"
                    f"👤 Raised by: {emp.name}<br>"
                    f"🏢 Office: {emp.office_location}<br>"
                    f"⚡ Priority: {ticket.priority}<br>"
                    f"{status_icon} Status: <strong>{ticket.status}</strong><br>"
                    f"📅 Created: {ticket.created_at.strftime('%d %b %Y, %I:%M %p')}<br>"
                    f"👨‍💼 Assigned To: {admin_name}<br>"
                    + (f"📋 Resolution: {ticket.resolution_notes}" if ticket.resolution_notes else '')
                )
                response['quick_replies'] = ['Report another issue', 'Search email', 'Go to home']
            else:
                response['text'] = (
                    f"❌ No ticket found with ID <code>{tid}</code>. Please check and try again."
                )
                response['quick_replies'] = ['Report an issue', 'Go to home']
        else:
            response['text'] = "Please provide your Ticket ID (e.g., <code>TKT1025</code>):"
        return response

    if intent in ('search_email', 'search_email_direct'):
        msg_lower = message.lower()
        designation_map = {
            'assistant engineer':      'Assistant Engineer',
            'executive engineer':      'Executive Engineer',
            'superintending engineer': 'Superintending Engineer',
            'junior engineer':         'Junior Engineer',
            'divisional engineer':     'Divisional Engineer',
            'chief engineer':          'Chief Engineer',
            ' ae ':  'Assistant Engineer',
            ' ee ':  'Executive Engineer',
            ' se ':  'Superintending Engineer',
            ' je ':  'Junior Engineer',
            ' de ':  'Divisional Engineer',
            ' ce ':  'Chief Engineer',
        }
        found_designation = None
        for key, val in designation_map.items():
            if key.strip() in msg_lower:
                found_designation = val
                break

        query = OfficialEmail.query
        if found_designation:
            query = query.filter(OfficialEmail.designation.ilike(f'%{found_designation}%'))

        stop_words = {
            'find','search','email','official','id','of','the','in','at','for',
            'assistant','executive','superintending','junior','divisional','chief','engineer',
        }
        words = [w for w in re.findall(r'[a-zA-Z]+', msg_lower)
                 if w not in stop_words and len(w) > 2]

        if words:
            location = words[-1].capitalize()
            query = query.filter(
                OfficialEmail.office.ilike(f'%{location}%') |
                OfficialEmail.district.ilike(f'%{location}%')
            )

        results = query.limit(5).all()
        if results:
            cards = ''.join(
                f"<div class='email-result-card'>"
                f"<strong>Position:</strong> {r.designation}<br>"
                f"<strong>Office:</strong> {r.office}<br>"
                f"<strong>Department:</strong> {r.department}<br>"
                f"<strong>District:</strong> {r.district}<br>"
                f"<strong>Email:</strong> <a href='mailto:{r.email_address}'>{r.email_address}</a>"
                f"</div>"
                for r in results
            )
            response['text'] = f"📧 <strong>Official Email Records Found:</strong><br><br>{cards}"
        else:
            response['text'] = (
                "❌ <strong>No official email record found</strong> for that query.<br><br>"
                "Try: <em>Assistant Engineer Madurai</em> or <em>Junior Engineer Coimbatore</em>"
            )
        response['quick_replies'] = ['Search another email', 'Report email issue', 'Go to home']
        return response

    if intent in ('mail_not_received', 'unable_to_send', 'login_failure', 'account_locked'):
        cat_map = {
            'mail_not_received': 'Mail Not Received',
            'unable_to_send':    'Unable To Send Email',
            'login_failure':     'Login Failure',
            'account_locked':    'Account Locked',
        }
        cat = cat_map[intent]
        response['session_data']['issue_category'] = cat
        response['session_data']['state'] = 'collect_issue_desc'
        response['text'] = (
            f"📌 <strong>{cat}</strong> — understood.<br><br>"
            "Please describe the issue in detail:<br>"
            "<em>(When did it start? Any error messages seen?)</em>"
        )
        return response

    if intent == 'thanks':
        response['text'] = (
            "😊 Happy to help! If you face any other issues, I'm here.<br><br>"
            "Have a productive day! 🙏"
        )
        response['quick_replies'] = ['Report another issue', 'Search email', 'Go to home']
        return response

    # Unknown
    response['text'] = (
        "🤔 I didn't quite understand that. Here's what I can help with:<br><br>"
        "📧 <strong>Search Official Email</strong><br>"
        "🔒 <strong>Report Email Issue</strong><br>"
        "🎫 <strong>Track Ticket</strong><br>"
        "🔑 <strong>Forgot Password</strong>"
    )
    response['quick_replies'] = [
        'Search Official Email', 'Report Email Issue', 'Track Ticket', 'Forgot Password'
    ]
    return response
