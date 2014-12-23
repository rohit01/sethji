# -*- coding: utf-8 -
#

import gevent
import gevent.monkey
gevent.monkey.patch_all()

from umbrella import app, ALL_RESOURCE_INDEX
from redis_handler import RedisHandler
import time


class TagReport(object):
    def __init__(self):
        self.redis_handler = RedisHandler(
            host=app.config.get('REDIS_HOST'),
            port=app.config.get('REDIS_PORT_NO'),
            password=app.config.get('REDIS_PASSWORD'),
            timeout=app.config.get('REDIS_TIMEOUT'),
        )


    def get_tags_info(self):
        return self.redis_handler.get_indexed_tags()


    def get_tag_resources(self, tag_key):
        tags_info = self.get_tags_info()
        tag_values = tags_info.get(tag_key, '')
        hash_set = set()
        for value in tag_values.split(','):
            if value.strip():
                hash_keys = self.redis_handler.get_index(value) or ''
                if hash_keys:
                    hash_set.update(hash_keys.split(','))
        all_hash_keys = self.redis_handler.get_index(ALL_RESOURCE_INDEX)
        all_hash_set = set(all_hash_keys.split(','))
        tag_resources = {
            tag_key: {
                'instance': [],
                'elb': [],
                'elastic_ip': [],
            },
            '--NOT-TRACKED--': {
                'instance': [],
                'elb': [],
                'elastic_ip': [],
            },
        }
        for key in all_hash_set:
            if not key.strip():
                continue
            details = self.redis_handler.get_details(key)
            if not details:
                continue
            if key in hash_set:
                category = tag_key
            else:
                category = '--NOT-TRACKED--'
            if key.startswith(self.redis_handler.instance_hash_prefix):
                tag_resources[category]['instance'].append(details)
            elif key.startswith(self.redis_handler.elb_hash_prefix):
                tag_resources[category]['elb'].append(details)
            elif key.startswith(self.redis_handler.elastic_ip_hash_prefix):
                tag_resources[category]['elastic_ip'].append(details)
            else:
                raise Exception("Unable to categorize info: %s" % str(details))
        return tag_resources


    def get_instance_details(self, region, instance_id):
        details = self.redis_handler.get_instance_details(region, instance_id)
        for tag_name in details.get('tag_keys', '').split(','):
            if not tag_name:
                continue
            if details.get('tag:%s' % tag_name):
                details['Tag - %s' % tag_name] = details.pop('tag:%s' % tag_name)
        if details.get('tag_keys'):
            details.pop('tag_keys')
        if details.get('timestamp'):
            time_now = int(round(time.time()))
            delay = time_now - int(details.pop('timestamp'))
            details['Last Checked'] = "%s seconds ago" % delay
        return details
