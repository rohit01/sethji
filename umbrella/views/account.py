# -*- coding: utf-8 -*-
#

from flask import Blueprint, render_template, request, redirect, url_for, \
    session, flash, g
from flask_oauthlib.client import OAuth
from umbrella import app
from umbrella.util import validate_email, pretty_date
from umbrella.model.sync import SyncAws
from functools import wraps
import time


mod = Blueprint('account', __name__, url_prefix='/account')

if app.config['LOGIN_ENABLED']:
    oauth = OAuth(app)
    google = oauth.remote_app(
        'google',
        consumer_key=app.config.get('GOOGLE_ID'),
        consumer_secret=app.config.get('GOOGLE_SECRET'),
        request_token_params={
            'scope': 'https://www.googleapis.com/auth/plus.login email'
        },
        base_url='https://www.googleapis.com/oauth2/v1/',
        request_token_url=None,
        access_token_method='POST',
        access_token_url='https://accounts.google.com/o/oauth2/token',
        authorize_url='https://accounts.google.com/o/oauth2/auth',
    )

    @google.tokengetter
    def get_google_oauth_token():
        return session.get('google_token')



def requires_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if app.config['LOGIN_ENABLED']:
            if not session.get('user_details'):
                flash(u'You need to be signed in for this page.')
                return redirect(url_for('account.index', next=request.path))
        auto_background_sync()
        return f(*args, **kwargs)
    return decorated_function


def auto_background_sync():
    sync_aws = SyncAws()
    g.is_syncing = sync_aws.is_sync_in_progress()
    last_sync_time = sync_aws.get_last_sync_time()
    g.last_update = pretty_date(last_sync_time)
    timeout = app.config.get('AUTO_REFRESH_TIMEOUT')
    if timeout:
        time_now = int(round(time.time()))
        if (time_now - last_sync_time) > timeout:
            sync_aws.background_sync()
            g.is_syncing = sync_aws.is_sync_in_progress()


def set_session_user_details():
    user_details = google.get('userinfo').data
    if 'error' in user_details:
        session.pop('google_token', None)
        return redirect(url_for('account.login'))
    authorized = validate_email(
        user_details.get('email', ''),
        app.config['AUTHORIZED_EMAILS'],
    )
    if not authorized:
        # TODO
        return "Unauthorized"
    session['user_details'] = user_details


@mod.route('/')
def index():
    if 'google_token' in session:
        set_session_user_details()
        return redirect(url_for('home'))
    return render_template('account/index.html')


@mod.route('/login')
def login():
    return google.authorize(callback=url_for('account.authorized',
                            _external=True))


@mod.route('/logout')
def logout():
    session.pop('google_token', None)
    session.pop('user_details', None)
    return redirect(url_for('account.index'))


@mod.route('/login/authorized')
def authorized():
    resp = google.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    session['google_token'] = (resp['access_token'], '')
    set_session_user_details()
    return redirect(url_for('home'))


