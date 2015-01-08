# -*- coding: utf-8 -*-
#

from sethji.model.report import TagReport
from flask import Blueprint, render_template, redirect, url_for, request
from sethji.util import pretty_date
from sethji.views.account import requires_login
from datetime import datetime
import time


mod = Blueprint('report', __name__, url_prefix='/report')
DEFAULT_REPORT = 'Owner'


def organize_details(item_details, friendly_names={}):
    tags = {}
    for tag_name in item_details.get('tag_keys', '').split(','):
        if not tag_name:
            continue
        if item_details.get('tag:%s' % tag_name):
            tags[tag_name] = item_details.pop('tag:%s' % tag_name)
    if item_details.get('tag_keys'):
        item_details.pop('tag_keys')
        item_details['tags'] = tags
    if item_details.get('timestamp'):
        time_now = int(round(time.time()))
        check_time = int(item_details.pop('timestamp'))
        item_details['Last checked'] = pretty_date(check_time)
    for k, v in friendly_names.items():
        if k in item_details:
            item_details[v] = item_details.pop(k)


@mod.route("/")
@requires_login
def index():
    reports = TagReport()
    tag_keys = reports.get_tags_info().keys()
    redirect_default = request.args.get('redirect', 'true').lower() == 'true'
    if (DEFAULT_REPORT in tag_keys) and redirect_default:
        return redirect(url_for('report.report', tag_name=DEFAULT_REPORT,
                        tag_value='all'))
    else:
        return render_template('report/index.html', tag_keys=tag_keys)


@mod.route("/<tag_name>/<tag_value>")
@requires_login
def report(tag_name, tag_value='all'):
    reports = TagReport()
    tags_info = reports.get_tags_info()
    if tag_name not in tags_info:
        return redirect(url_for('report.index', redirect=False))
    tag_resources = reports.get_tag_resources(tag_name, tag_value)
    return render_template(
        'report/report.html',
        tags_info=tags_info,
        selected_tag=tag_name,
        selected_tag_value=tag_value,
        tag_resources=tag_resources,
    )


@mod.route("/instance/<region>/<instance_id>")
@requires_login
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
        'root_device_type': 'Root Device Type',
        'ebs_optimized': 'EBS Optimized',
        'ebs_ids': 'EBS Volumes',
        'launch_time': 'Launch Time',
        'architecture': 'Architecture',
        'vpc_id': 'VPC ID',
    }
    page_meta = {
        'title': "Instance details - %s" % instance_id,
        'name': "EC2 instance details",
        '404': "Instance not found!",
    }
    reports = TagReport()
    details = reports.get_instance_details(region, instance_id)
    if details.get('launch_time'):
        launch_time = datetime.strptime(
            details.get('launch_time').split('.')[0], "%Y-%m-%dT%H:%M:%S")
        details['launch_time'] = pretty_date(launch_time)
    organize_details(details, friendly_names)
    return render_template(
        'report/item_details.html',
        item_details=details,
        page_meta=page_meta,
    )


@mod.route("/ebs_volume/<region>/<volume_id>")
@requires_login
def ebs_volume_details(region, volume_id):
    friendly_names = {
        'create_time': 'Create Time',
        'volume_id': 'Volume ID',
        'instance_id': 'Instance ID',
        'iops': 'IOPS',
        'region': 'Region',
        'size': 'Size (in GB)',
        'snapshot_id': 'Snapshot ID',
        'status': 'Status',
        'type': 'Type',
        'zone': 'Zone',
    }
    page_meta = {
        'title': "EBS volume details - %s" % volume_id,
        'name': "EBS volume details",
        '404': "EBS volume not found!",
    }
    reports = TagReport()
    details = reports.get_ebs_volume_details(region, volume_id)
    if 'create_time' in details:
        create_time = datetime.strptime(
            details.get('create_time').split('.')[0], "%Y-%m-%dT%H:%M:%S")
        details['create_time'] = pretty_date(create_time)
    organize_details(details, friendly_names)
    return render_template(
        'report/item_details.html',
        item_details=details,
        page_meta=page_meta,
    )


@mod.route("/elb/<region>/<elb_name>")
@requires_login
def elb_details(region, elb_name):
    friendly_names = {
        'elb_name': 'ELB Name',
        'region': 'Region',
        'elb_dns': 'DNS',
        'elb_instances': 'Instances',
        'subnets': 'Subnets',
        'created_time': 'Created Time',
        'vpc_id': 'VPC ID',
    }
    page_meta = {
        'title': "ELB details - %s" % elb_name,
        'name': "Elastic load balancer details",
        '404': "Elastic load balancer not found!",
    }
    reports = TagReport()
    details = reports.get_elb_details(region, elb_name)
    if 'elb_instances' in details:
        details['elb_instances'] = details['elb_instances'].replace(',', ', ')
    if 'created_time' in details:
        created_time = datetime.strptime(
            details.get('created_time').split('.')[0], "%Y-%m-%dT%H:%M:%S")
        details['created_time'] = pretty_date(created_time)
    organize_details(details, friendly_names)
    return render_template(
        'report/item_details.html',
        item_details=details,
        page_meta=page_meta,
    )


@mod.route("/elastic_ip/<elastic_ip>")
@requires_login
def elastic_ip_details(elastic_ip):
    friendly_names = {
        'region': 'Region',
        'elastic_ip': 'Elastic IP',
        'instance_id': 'Instance ID',
    }
    page_meta = {
        'title': "Elastic IP details - %s" % elastic_ip,
        'name': "Elastic IP details",
        '404': "Elastic IP not found!",
    }
    reports = TagReport()
    details = reports.get_elastic_ip_details(elastic_ip)
    organize_details(details, friendly_names)
    return render_template(
        'report/item_details.html',
        item_details=details,
        page_meta=page_meta,
    )
