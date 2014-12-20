# -*- coding: utf-8 -*-
#

import umbrella.sync

@app.route("/sync")
def sync():
    umbrella.sync.sync_aws()
    return 'Sync Complete'
