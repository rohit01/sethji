# -*- coding: utf-8 -*-
#

from flask import Blueprint, render_template, request, redirect, url_for, \
    session, flash, g
from flask_oauthlib.client import OAuth
from sethji import app
from sethji.util import validate_email, pretty_date
from sethji.model.sync import SyncAws
from functools import wraps
import time
import requests
import json
from urllib import urlencode


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
        if app.config.get('LOGIN_ENABLED'):
            if not session.get('user_details'):
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
        session.pop('google_token', None)
        flash(u'Unauthorized access. Please contact admin to get access!')
        return False
    session['user_details'] = user_details
    return True


@mod.route('/')
def index():
    if 'google_token' in session:
        if not set_session_user_details():
            return render_template('account/index.html')
        return redirect(url_for('home'))
    if request.args.get('next', None):
        session['next'] = request.args.get('next', None)
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
    next_page = url_for('home')
    if 'next' in session:
        next_page = session.pop('next')
    resp = google.authorized_response()
    if resp is None:
        flash(u'Access denied: reason=%s error=%s' % 
            (request.args['error_reason'], request.args['error_description'])
        )
        return redirect(url_for('account.index', next=next_page))
    session['google_token'] = (resp['access_token'], '')
    if not set_session_user_details():
        return redirect(url_for('account.index', next=next_page))
    if session.get('user_details', {}).get('given_name'):
        first_name = session.get('user_details', {}).get('given_name')
        last_name = session.get('user_details', {}).get('family_name')
        flash("Welcome! %s" % welcome_joke(first_name, last_name))
    return redirect(next_page)


def welcome_joke(first_name, last_name):
    params = {
        'limitTo': '[nerdy]',
    }
    if first_name:
        params['firstName'] = first_name
    if last_name:
        params['lastName'] = last_name
    url = "http://api.icndb.com/jokes/random?%s" % urlencode(params)
    try:
        resp = requests.get(url, timeout=2)
        if 200 <= resp.status_code < 300:
            content = json.loads(resp.text)
            message = content.get(u'value', {}).get(u'joke')
            if not message:
                message = 'Welcome %s!' % first_name
    except Exception:
        message = 'Welcome %s!' % first_name
    return message
