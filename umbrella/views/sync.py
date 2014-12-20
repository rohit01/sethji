# -*- coding: utf-8 -*-
#

from umbrella.model.sync import sync_aws
from flask import Blueprint


mod = Blueprint('sync', __name__, url_prefix='/sync')


@mod.route("/")
def sync():
    sync_aws()
    return 'Sync Complete'
