# -*- coding: utf-8 -
#

import gevent
import gevent.monkey
gevent.monkey.patch_all()

from umbrella import app
from redis_handler import RedisHandler


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
                hash_set.update(hash_keys.split(','))
        tag_resources = {
            'instance': [],
            'elb': [],
            'elastic_ip': [],
        }
        for key in hash_set:
            if not key.strip():
                continue
            details = self.redis_handler.get_details(key)
            if not details:
                continue
            if key.startswith(self.redis_handler.instance_hash_prefix):
                tag_resources['instance'].append(details)
            elif key.startswith(self.redis_handler.elb_hash_prefix):
                tag_resources['elb'].append(details)
            elif key.startswith(self.redis_handler.elastic_ip_hash_prefix):
                tag_resources['elastic_ip'].append(details)
            else:
                raise Exception("Unable to categorize info: %s" % str(details))
        return tag_resources
