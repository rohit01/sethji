# -*- coding: utf-8 -*-
#

from umbrella.model.sync import sync_aws
from flask import Blueprint, render_template


mod = Blueprint('report', __name__, url_prefix='/report')


@mod.route("/")
def report():
    report_aws()
    return render_template('report/index.html')
