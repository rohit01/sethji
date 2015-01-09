# -*- coding: utf-8 -
#

import gevent
import gevent.monkey
gevent.monkey.patch_all()

from sethji import app, ALL_RESOURCE_INDEX
from redis_handler import RedisHandler
from functools import wraps
from flask import g
import time
import json


class TagReport(object):
    def __init__(self):
        self.redis_handler = RedisHandler(
            host=app.config.get('REDIS_HOST'),
            port=app.config.get('REDIS_PORT_NO'),
            password=app.config.get('REDIS_PASSWORD'),
            idle_timeout=app.config.get('REDIS_IDLE_TIMEOUT'),
        )
        self.get_tag_resources = self._cache_function(self.get_tag_resources)


    def _cache_function(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            kwargs_keys = kwargs.keys()
            kwargs_keys.sort()
            path = "%s/%s/%s" % (f.func_name, '/'.join(args),
                '/'.join(['%s=%s' % (k, kwargs[k]) for k in kwargs_keys]))
            cached_response = self.redis_handler.get_cached_object(path)
            if cached_response:
                return json.loads(cached_response)
            response = f(*args, **kwargs)
            expire_duration = app.config.get('EXPIRE_DURATION')
            gevent.spawn_raw(self.redis_handler.set_object_cache, path,
                             json.dumps(response), expire_duration)
            return response
        return decorated_function


    def get_tags_info(self):
        return self.redis_handler.get_indexed_tags()


    def get_tag_resources(self, tag_key, tag_value=None):
        tags_info = self.get_tags_info()
        if (not tag_value) or (tag_value.lower() == 'all'):
            process_tag_values = tags_info.get(tag_key, '')
        else:
            process_tag_values = tag_value
        hash_set = set()
        for value in process_tag_values.split(','):
            if value.strip():
                hash_keys = self.redis_handler.get_index(value) or ''
                if hash_keys:
                    hash_set.update(hash_keys.split(','))
        # All Hash keys
        all_hash_keys = self.redis_handler.get_index(ALL_RESOURCE_INDEX)
        all_hash_set = set(all_hash_keys.split(','))
        # Tagged resources
        tag_resources = {
            tag_key: {
                'instance': [],
                'elb': [],
                'elastic_ip': [],
                'ebs_volumes': [],
            }
        }
        if (not tag_value) or (tag_value.lower() == 'all'):
            tag_resources['--NOT-TRACKED--'] = {
                'instance': [],
                'elb': [],
                'elastic_ip': [],
                'ebs_volumes': [],
            }
        # Get details
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
            if category not in tag_resources:
                continue
            if key.startswith(self.redis_handler.instance_hash_prefix):
                tag_resources[category]['instance'].append(details)
            elif key.startswith(self.redis_handler.elb_hash_prefix):
                tag_resources[category]['elb'].append(details)
            elif key.startswith(self.redis_handler.elastic_ip_hash_prefix):
                tag_resources[category]['elastic_ip'].append(details)
            elif key.startswith(self.redis_handler.ebs_vol_hash_prefix):
                tag_resources[category]['ebs_volumes'].append(details)
            else:
                raise Exception("Unable to categorize info: %s" % str(details))
        return tag_resources


    def get_instance_details(self, region, instance_id):
        return self.redis_handler.get_instance_details(region, instance_id)


    def get_ebs_volume_details(self, region, volume_id):
        return self.redis_handler.get_ebs_volume_details(region, volume_id)


    def get_elb_details(self, region, elb_name):
        return self.redis_handler.get_elb_details(region, elb_name)


    def get_elastic_ip_details(self, elastic_ip):
        return self.redis_handler.get_elastic_ip_details(elastic_ip)
