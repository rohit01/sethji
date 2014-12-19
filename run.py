# -*- coding: utf-8 -*-
#
# Python flask application to be deployed as a heroku application
#
# Author - @rohit01
# -----------------

import flask
import os
import umbrella
import umbrella.sync
import umbrella.config

app = flask.Flask(__name__)


@app.route('/favicon.ico')
def favicon():
    return flask.send_from_directory(
        os.path.join(app.root_path, 'umbrella', 'static'), 'favicon.ico')


@app.route("/version")
def status():
    return 'Ok - Version: %s' % umbrella.__version__

@app.route("/sync")
def sync():
    umbrella.sync.sync_aws()
    return 'Ok - Version: %s' % umbrella.__version__


if __name__ == '__main__':
    app.run(host=umbrella.config.HOST, port=umbrella.config.PORT, 
            debug=umbrella.config.DEBUG)
