from flask import redirect, url_for, Blueprint, render_template, request, flash
from flask_login import login_user, logout_user, current_user
from g_tracker import db
from g_tracker.forms import LoginForm, RegistrationForm
from g_tracker.models import Person
# from werkzeug.urls import url_parse
from urllib.parse import urlparse

bp = Blueprint('auth', __name__)


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
