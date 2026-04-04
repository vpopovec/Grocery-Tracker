import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_user, logout_user
from sqlalchemy import or_
from urllib.parse import urlparse

from g_tracker import db
from g_tracker.forms import (
    ForgotPasswordForm,
    LoginForm,
    RegistrationForm,
    ResetPasswordForm,
)
from g_tracker.models import PasswordResetToken, Person

bp = Blueprint('auth', __name__)


def _require_dev_password_reset():
    if not current_app.config.get('ENABLE_DEV_PASSWORD_RESET'):
        abort(404)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _lookup_valid_token(raw: str) -> Optional[PasswordResetToken]:
    if not raw:
        return None
    row = PasswordResetToken.query.filter_by(
        token_hash=_hash_token(raw.strip())).first()
    if row is None or not row.is_valid():
        return None
    return row


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # TODO: Create a Dashboard
        return redirect(url_for('item_table.receipts'))
    form = LoginForm()
    if form.validate_on_submit():
        person = Person.query.filter_by(username=form.username.data).first()
        if person is None or not person.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))
        login_user(person, remember=form.remember_me.data)

        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('welcome.index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('welcome.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        # TODO: Create a Dashboard
        return redirect(url_for('item_table.receipts'))
    form = RegistrationForm()
    if form.validate_on_submit():
        person = Person(username=form.username.data, email=form.email.data, name=form.nickname.data)
        person.set_password(form.password.data)
        print(f"REGISTERED {person}")

        db.session.add(person)
        db.session.commit()

        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('auth.login'))
    return render_template('register.html', title='Register', form=form)


@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    _require_dev_password_reset()
    if current_user.is_authenticated:
        return redirect(url_for('item_table.receipts'))
    form = ForgotPasswordForm()
    submitted = False
    reset_url = None
    if form.validate_on_submit():
        submitted = True
        ident = form.identifier.data.strip()
        person = Person.query.filter(
            or_(Person.username == ident, Person.email == ident)).first()
        if person:
            PasswordResetToken.query.filter(
                PasswordResetToken.person_id == person.person_id,
                PasswordResetToken.used_at.is_(None),
            ).delete(synchronize_session=False)
            raw = secrets.token_urlsafe(32)
            db.session.add(PasswordResetToken(
                person_id=person.person_id,
                token_hash=_hash_token(raw),
                expires_at=datetime.utcnow() + timedelta(hours=1),
            ))
            db.session.commit()
            reset_url = url_for('auth.reset_password', token=raw, _external=True)
        return render_template(
            'forgot_password.html',
            title='Forgot password',
            form=ForgotPasswordForm(),
            submitted=submitted,
            reset_url=reset_url,
        )
    return render_template(
        'forgot_password.html',
        title='Forgot password',
        form=form,
        submitted=submitted,
        reset_url=reset_url,
    )


@bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    _require_dev_password_reset()
    if current_user.is_authenticated:
        return redirect(url_for('item_table.receipts'))

    if request.method == 'POST':
        form = ResetPasswordForm()
        if form.validate_on_submit():
            row = _lookup_valid_token(form.token.data)
            if row is None:
                flash('Invalid or expired reset link.')
                return redirect(url_for('auth.login'))
            person = db.session.get(Person, row.person_id)
            person.set_password(form.password.data)
            row.used_at = datetime.utcnow()
            db.session.commit()
            flash('Your password has been reset. You can sign in now.')
            return redirect(url_for('auth.login'))
        raw = (form.token.data or '').strip()
        row = _lookup_valid_token(raw)
        if row is None:
            flash('Invalid or expired reset link.')
            return redirect(url_for('auth.login'))
        return render_template(
            'reset_password.html', title='Set new password', form=form)

    raw = request.args.get('token', '').strip()
    row = _lookup_valid_token(raw)
    if row is None:
        flash('Invalid or expired reset link.')
        return redirect(url_for('auth.login'))
    form = ResetPasswordForm(token=raw)
    return render_template('reset_password.html', title='Set new password', form=form)
