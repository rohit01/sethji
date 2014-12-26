# -*- coding: utf-8 -*-
#

from umbrella.model.sync import SyncAws
from umbrella.views.account import requires_login
from flask import Blueprint, redirect, url_for, flash


mod = Blueprint('sync', __name__, url_prefix='/sync')


@mod.route("/", methods=["POST"])
@requires_login
def sync():
    sync_aws = SyncAws()
    sync_aws.background_sync()
    flash(u'AWS Sync Initiated')
    return redirect(url_for('home'))


def is_sync_in_progress():
    sync_aws = SyncAws()
    return sync_aws.is_sync_in_progress()
