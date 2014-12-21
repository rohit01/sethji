# -*- coding: utf-8 -*-
#

from umbrella.model.sync import SyncAws
from flask import Blueprint, render_template


mod = Blueprint('sync', __name__, url_prefix='/sync')


@mod.route("/")
def sync():
    sync_aws = SyncAws()
    sync_aws.sync()
    return render_template('sync/index.html', message="Sync Complete")
