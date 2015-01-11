# -*- coding: utf-8 -*-
#

from sethji.model.sync import SyncAws
from sethji.views.account import requires_login
from flask import Blueprint, redirect, url_for, flash, request


mod = Blueprint('sync', __name__, url_prefix='/sync')


@mod.route("/", methods=["POST"])
@requires_login
def sync():
    sync_aws = SyncAws()
    sync_aws.background_sync()
    flash(u'AWS Sync Initiated')
    next_page = url_for('home')
    if 'next' in request.args:
        next_page = request.args.get('next')
    return redirect(next_page)


def is_sync_in_progress():
    sync_aws = SyncAws()
    return sync_aws.is_sync_in_progress()
