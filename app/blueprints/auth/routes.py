from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.blueprints.auth import auth
from app.models import User, Employee, OfficialEmail, PasswordResetRequest, db
from datetime import datetime
import random


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_request_id():
    """Generate a unique PWD-prefixed request ID."""
    for _ in range(10):
        rid = f"PWD{random.randint(100, 9999)}"
        if not PasswordResetRequest.query.filter_by(request_id=rid).first():
            return rid
    # Fallback: use timestamp
    return f"PWD{int(datetime.utcnow().timestamp())}"


def _generate_temp_password():
    """Generate a readable temporary password."""
    import string
    chars = string.ascii_letters + string.digits
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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role     = request.form.get('role', 'employee')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active:
            if role == 'admin' and not user.is_admin:
                flash('You do not have admin privileges.', 'danger')
                return render_template('auth/login.html')
            if role == 'employee' and user.is_admin:
                flash('Please use Admin Login for admin accounts.', 'warning')
                return render_template('auth/login.html')

            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()

            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('employee.dashboard'))
        else:
            flash('Invalid credentials. Please check your Employee ID and password.', 'danger')

    return render_template('auth/login.html')


# ── Logout ────────────────────────────────────────────────────────────────────

@auth.route('/logout')
@login_required
def logout():
    logout_user()
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

        # ── Validation ────────────────────────────────────────
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

        # ── Look up employee ──────────────────────────────────
        employee = Employee.query.filter_by(
            employee_id=employee_id_input,
            is_active=True
        ).first()

        if not employee:
            flash('No active employee found with that Employee ID.', 'danger')
            return render_template('auth/forgot_password.html',
                                   form_data=request.form)

        # ── Verify phone ──────────────────────────────────────
        # Strip non-digits for comparison
        submitted_phone = ''.join(filter(str.isdigit, phone_input))
        stored_phone    = ''.join(filter(str.isdigit, employee.phone or ''))
        if submitted_phone != stored_phone:
            flash('Mobile number does not match our records for this Employee ID.', 'danger')
            return render_template('auth/forgot_password.html',
                                   form_data=request.form)

        # ── Verify official email ─────────────────────────────
        official_email_record = OfficialEmail.query.filter_by(
            employee_id_fk=employee.id,
            is_active=True
        ).first()

        if not official_email_record:
            flash('No official email record found for this employee. Contact IT directly.', 'danger')
            return render_template('auth/forgot_password.html',
                                   form_data=request.form)

        if email_input != official_email_record.email_address.lower():
            flash('Official email address does not match our records.', 'danger')
            return render_template('auth/forgot_password.html',
                                   form_data=request.form)

        # ── Check for existing pending request ────────────────
        existing = PasswordResetRequest.query.filter_by(
            employee_id_fk=employee.id,
            status='Pending'
        ).first()
        if existing:
            flash(
                f'You already have a pending reset request ({existing.request_id}). '
                'Please wait for admin approval or contact IT support.',
                'warning'
            )
            return render_template('auth/forgot_password.html',
                                   form_data=request.form)

        # ── Create request ────────────────────────────────────
        pr = PasswordResetRequest(
            request_id             = _generate_request_id(),
            employee_id_fk         = employee.id,
            employee_name          = employee.name,
            designation            = employee.designation,
            office_location        = employee.office_location,
            phone                  = phone_input,
            official_email_submitted = email_input,
            reason                 = reason_input,
            status                 = 'Pending',
        )
        db.session.add(pr)
        db.session.commit()

        return render_template('auth/forgot_password_success.html',
                               request_id=pr.request_id,
                               employee_name=employee.name)

    return render_template('auth/forgot_password.html', form_data={})
