from flask import render_template, flash, redirect, url_for
from flask import request
from flask_login import current_user, login_user, logout_user
from werkzeug.urls import url_parse
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from app.models import User


@bp.route('/login', methods=['GET', 'POST'])
def login():
    # use flask-login extension provided mixin methods
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    # Form.validate_on_submit() will first check if request is GET or POST,
    # it returns False if request is GET, for POST then it validates submitted
    # form content in the request POST body.
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash(f'Login failed for user {form.username.data}', category='error')
            return redirect(url_for('auth.login'))

        # register authenticated user
        login_user(user, remember=form.remember_me.data)
        # after login success, redirect user to last intended url
        # if the login is from @login_required interception from flask-login
        # extension, the original url is included in request param 'next'
        next_page = request.args.get('next')
        # if login is not from intercepted request url, use default url
        # or if the intercepted request url is not a relative path (aka an url
        # without the domain portion), that could be an external attack,
        # in this case ignore that request, use default url
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)

    return render_template('auth/login.html', title='Sign In', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash('You are already registered')
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('You have successfully registered')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', title='Register', form=form)
