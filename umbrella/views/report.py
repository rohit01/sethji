# -*- coding: utf-8 -*-
#

from umbrella.model.report import TagReport
from flask import Blueprint, render_template, redirect, url_for, request


mod = Blueprint('report', __name__, url_prefix='/report')
DEFAULT_REPORT = 'Owner'


@mod.route("/")
def index():
    reports = TagReport()
    tag_keys = reports.get_tags_info().keys()
    redirect_default = request.args.get('redirect', 'true').lower() == 'true'
    if (DEFAULT_REPORT in tag_keys) and redirect_default:
        return redirect(url_for('report.report', tag_name=DEFAULT_REPORT))
    else:
        return render_template('report/index.html', tag_keys=tag_keys)


@mod.route("/<tag_name>")
def report(tag_name):
    reports = TagReport()
    tag_keys = reports.get_tags_info().keys()
    if tag_name not in tag_keys:
        return redirect(url_for('report.index', redirect=False))
    tag_resources = reports.get_tag_resources(tag_name)
    return render_template(
        'report/report.html',
        tag_keys=tag_keys,
        selected_tag=tag_name,
        tag_resources=tag_resources,
    )

@mod.route("/instance/<region>/<instance_id>")
def instance_details(region, instance_id):
    reports = TagReport()
    instance_details = reports.get_instance_details(region, instance_id)
    return render_template(
        'report/instance_details.html',
        instance_details=instance_details
    )
