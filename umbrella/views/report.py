# -*- coding: utf-8 -*-
#

from umbrella.model.report import TagReport
from flask import Blueprint, render_template, redirect, url_for, request
from umbrella.util import pretty_date
import time


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
    friendly_names = {
        'zone': 'Zone',
        'instance_type': 'Instance Type',
        'ec2_private_dns': 'Private DNS',
        'region': 'Region',
        'state': 'State',
        'instance_id': 'Instance ID',
        'ec2_dns': 'Public DNS',
        'private_ip_address': 'Private IP Address',
        'ip_address': 'IP Address',
        'instance_elb_names': 'ELB Name(s)',
    }
    reports = TagReport()
    details = reports.get_instance_details(region, instance_id)
    tags = {}
    for tag_name in details.get('tag_keys', '').split(','):
        if not tag_name:
            continue
        if details.get('tag:%s' % tag_name):
            tags[tag_name] = details.pop('tag:%s' % tag_name)
    if details.get('tag_keys'):
        details.pop('tag_keys')
        details['tags'] = tags
    if details.get('timestamp'):
        time_now = int(round(time.time()))
        check_time = int(details.pop('timestamp'))
        details['Last checked'] = pretty_date(check_time)
    for k, v in friendly_names.items():
        if k in details:
            details[v] = details.pop(k)
    return render_template(
        'report/instance_details.html',
        instance_details=details
    )


@mod.route("/elb/<region>/<elb_name>")
def elb_details(region, elb_name):
    friendly_names = {
        'elb_name': 'ELB Name',
        'region': 'Region',
        'elb_dns': 'DNS',
        'elb_instances': 'Instances',
    }
    reports = TagReport()
    details = reports.get_elb_details(region, elb_name)
    tags = {}
    for tag_name in details.get('tag_keys', '').split(','):
        if not tag_name:
            continue
        if details.get('tag:%s' % tag_name):
            tags[tag_name] = details.pop('tag:%s' % tag_name)
    if details.get('tag_keys'):
        details.pop('tag_keys')
        details['tags'] = tags
    if details.get('timestamp'):
        time_now = int(round(time.time()))
        check_time = int(details.pop('timestamp'))
        details['Last checked'] = pretty_date(check_time)
    if 'elb_instances' in details:
        details['elb_instances'] = details['elb_instances'].replace(',', ', ')
    for k, v in friendly_names.items():
        if k in details:
            details[v] = details.pop(k)
    return render_template(
        'report/elb_details.html',
        instance_details=details
    )
