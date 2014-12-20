# -*- coding: utf-8 -*-
#
# Python flask application to be deployed as a heroku application
#
# Author - @rohit01
# -----------------

from umbrella import app
from config import HOST, PORT, DEBUG


if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=DEBUG)
