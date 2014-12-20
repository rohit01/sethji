# -*- coding: utf-8 -
#

import flask
import os
import umbrella.config


app = flask.Flask(__name__)
app.config.from_object('config')


@app.errorhandler(404)
def not_found(error):
    return flask.render_template('404.html'), 404


@app.route('/favicon.ico')
def favicon():
    return flask.send_from_directory(
        os.path.join(app.root_path, 'static'), 'favicon.ico')
