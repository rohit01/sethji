# -*- coding: utf-8 -
#

from flask import Flask, render_template, send_from_directory, redirect, url_for
from raven.contrib.flask import Sentry
import os


app = Flask(__name__)
app.config.from_object('config')
if app.config.get('SENTRY_DSN'):
    Sentry(app)


ALL_RESOURCE_INDEX = '__ALL_RESOURCE_INDEX__'


from sethji.views import sync, report, account
app.register_blueprint(sync.mod)
app.register_blueprint(report.mod)
app.register_blueprint(account.mod)


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'), 'favicon.png')


@app.route('/')
@account.requires_login
def home():
    return redirect(url_for('report.index'))
