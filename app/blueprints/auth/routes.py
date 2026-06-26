from flask import render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.blueprints.auth import auth
from app.models import User, Employee, OfficialEmail, PasswordResetRequest, db
from datetime import datetime
import random


# ── CAPTCHA helpers ───────────────────────────────────────────────────────────

def _generate_captcha():
    """
    Build a random arithmetic CAPTCHA, store the answer in the session,
    and return the question string to render in the template.

    Operations: addition, subtraction (result always ≥ 0), multiplication.
    Numbers are kept small so the answer fits in a single input easily.
    """
    op = random.choice(['add', 'sub', 'mul'])

    if op == 'add':
        a, b = random.randint(1, 20), random.randint(1, 20)
        question = f"{a} + {b} = ?"
        answer   = a + b

    elif op == 'sub':
        a = random.randint(5, 20)
        b = random.randint(1, a)          # guarantee b ≤ a so result ≥ 0
        question = f"{a} \u2212 {b} = ?"  # − (minus sign, not hyphen)
        answer   = a - b

    else:  # mul
        a, b = random.randint(2, 9), random.randint(2, 9)
        question = f"{a} \u00d7 {b} = ?"  # × (multiplication sign)
        answer   = a * b

    session['captcha_answer'] = answer
    return question


def _verify_captcha(user_input: str) -> bool:
    """Return True only when the submitted value matches the session answer."""
    try:
        submitted = int(user_input.strip())
    except (ValueError, AttributeError):
        return False
    expected = session.get('captcha_answer')
    return expected is not None and submitted == expected


# ── Other helpers ─────────────────────────────────────────────────────────────

def _generate_request_id():
    """Generate a unique PWD-prefixed request ID."""
    for _ in range(10):
        rid = f"PWD{random.randint(100, 9999)}"
        if not PasswordResetRequest.query.filter_by(request_id=rid).first():
            return rid
    return f"PWD{int(datetime.utcnow().timestamp())}"


def _generate_temp_password():
    """Generate a readable temporary password."""
    import string
    chars  = string.ascii_letters + string.digits
    suffix = ''.join(random.choices(chars, k=6))
    return f"Temp@{suffix}"


# ── Login ─────────────────────────────────────────────────────────────────────

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('employee.dashboard'))

    if request.method == 'POST':
        username      = request.form.get('username', '').strip()
        password      = request.form.get('password', '')
        role          = request.form.get('role', 'employee')
        captcha_input = request.form.get('captcha', '')

        # ── Step 1: verify CAPTCHA before touching credentials ──
        if not _verify_captcha(captcha_input):
            flash('Incorrect CAPTCHA. Please try again.', 'danger')
            captcha_question = _generate_captcha()          # fresh question
            return render_template('auth/login.html',
                                   captcha_question=captcha_question)

        # ── Step 2: authenticate ────────────────────────────────
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active:
            if role == 'admin' and not user.is_admin:
                flash('You do not have admin privileges.', 'danger')
                captcha_question = _generate_captcha()
                return render_template('auth/login.html',
                                       captcha_question=captcha_question)
            if role == 'employee' and user.is_admin:
                flash('Please use Admin Login for admin accounts.', 'warning')
                captcha_question = _generate_captcha()
                return render_template('auth/login.html',
                                       captcha_question=captcha_question)

            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            session.pop('captcha_answer', None)   # clear used answer

            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('employee.dashboard'))

        else:
            flash('Invalid credentials. Please check your Employee ID and password.', 'danger')
            captcha_question = _generate_captcha()          # new CAPTCHA on failed login
            return render_template('auth/login.html',
                                   captcha_question=captcha_question)

    # GET — always generate a fresh CAPTCHA
    captcha_question = _generate_captcha()
    return render_template('auth/login.html', captcha_question=captcha_question)


# ── Logout ────────────────────────────────────────────────────────────────────

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('captcha_answer', None)   # clear so next login gets a fresh one
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('auth.login'))


# ── Forgot Password (public — no login required) ──────────────────────────────

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Public page — accessible without logging in.
    Validates employee identity via Employee ID + phone + official email,
    then creates a PasswordResetRequest for admin approval.
    """
    if current_user.is_authenticated:
        return redirect(url_for('employee.dashboard'))

    if request.method == 'POST':
        employee_id_input = request.form.get('employee_id', '').strip().upper()
        phone_input       = request.form.get('phone', '').strip()
        email_input       = request.form.get('official_email', '').strip().lower()
        reason_input      = request.form.get('reason', '').strip()

        errors = []
        if not employee_id_input:
            errors.append('Employee ID is required.')
        if not phone_input:
            errors.append('Registered Mobile Number is required.')
        if not email_input:
            errors.append('Official Email Address is required.')
        if not reason_input:
            errors.append('Reason for password reset is required.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('auth/forgot_password.html',
                                   form_data=request.form)

        employee = Employee.query.filter_by(
            employee_id=employee_id_input, is_active=True
        ).first()

        if not employee:
            flash('No active employee found with that Employee ID.', 'danger')
            return render_template('auth/forgot_password.html',
                                   form_data=request.form)

        submitted_phone = ''.join(filter(str.isdigit, phone_input))
        stored_phone    = ''.join(filter(str.isdigit, employee.phone or ''))
        if submitted_phone != stored_phone:
            flash('Mobile number does not match our records for this Employee ID.', 'danger')
            return render_template('auth/forgot_password.html',
                                   form_data=request.form)

        official_email_record = OfficialEmail.query.filter_by(
            employee_id_fk=employee.id, is_active=True
        ).first()

        if not official_email_record:
            flash('No official email record found for this employee. Contact IT directly.', 'danger')
            return render_template('auth/forgot_password.html',
                                   form_data=request.form)

        if email_input != official_email_record.email_address.lower():
            flash('Official email address does not match our records.', 'danger')
            return render_template('auth/forgot_password.html',
                                   form_data=request.form)

        existing = PasswordResetRequest.query.filter_by(
            employee_id_fk=employee.id, status='Pending'
        ).first()
        if existing:
            flash(
                f'You already have a pending reset request ({existing.request_id}). '
                'Please wait for admin approval or contact IT support.',
                'warning'
            )
            return render_template('auth/forgot_password.html',
                                   form_data=request.form)

        pr = PasswordResetRequest(
            request_id               = _generate_request_id(),
            employee_id_fk           = employee.id,
            employee_name            = employee.name,
            designation              = employee.designation,
            office_location          = employee.office_location,
            phone                    = phone_input,
            official_email_submitted = email_input,
            reason                   = reason_input,
            status                   = 'Pending',
        )
        db.session.add(pr)
        db.session.commit()

        return render_template('auth/forgot_password_success.html',
                               request_id=pr.request_id,
                               employee_name=employee.name)

    return render_template('auth/forgot_password.html', form_data={})