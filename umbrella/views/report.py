# -*- coding: utf-8 -*-
#

from umbrella.model.report import TagReport
from flask import Blueprint, render_template, redirect, url_for


mod = Blueprint('report', __name__, url_prefix='/report')
DEFAULT_REPORT = 'Owner'


@mod.route("/")
def index():
    reports = TagReport()
    tag_keys = reports.get_tags_info().keys()
    if DEFAULT_REPORT in tag_keys:
        return redirect(url_for('report.report', tag_name=DEFAULT_REPORT))
    else:
        return render_template('report/index.html')


@mod.route("/<tag_name>")
def report(tag_name):
    reports = TagReport()
    tag_keys = reports.get_tags_info().keys()
    tag_resources = reports.get_tag_resources(tag_name)
    return render_template(
        'report/report.html',
        tag_keys=tag_keys,
        selected_tag=tag_name,
        tag_resources=tag_resources,
    )
