# -*- coding: utf-8 -
#

import gevent
import gevent.monkey
gevent.monkey.patch_all()

from sethji import app, ALL_RESOURCE_INDEX
from sethji.util import get_current_month_day_count
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
        tags_info = self.redis_handler.get_indexed_tags()
        for k, v in tags_info.items():
            if not v:
                tags_info[k] = []
                continue
            value_list = []
            for key_value in v.split(','):
                if key_value.startswith('%s:' % k):
                    value_list.append(key_value[(len(k) + 1):])
                else:
                    value_list.append(key_value)
            tags_info[k] = value_list
        return tags_info


    def get_tag_resources(self, tag_key, tag_value=None):
        tags_info = self.get_tags_info()
        if (not tag_value) or (tag_value.lower() == 'all'):
            process_tag_values = tags_info.get(tag_key, [])
        else:
            process_tag_values = tag_value.split(',')
        hash_set = set()
        for value in process_tag_values:
            if value.strip():
                value = "%s:%s" % (tag_key, value)
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
                'ebs_snapshots': [],
            }
        }
        if (not tag_value) or (tag_value.lower() == 'all'):
            tag_resources['--NOT-TRACKED--'] = {
                'instance': [],
                'elb': [],
                'elastic_ip': [],
                'ebs_volumes': [],
                'ebs_snapshots': [],
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
            details = self._cal_monthly_cost(details)
            if key.startswith(self.redis_handler.instance_hash_prefix):
                tag_resources[category]['instance'].append(details)
            elif key.startswith(self.redis_handler.elb_hash_prefix):
                tag_resources[category]['elb'].append(details)
            elif key.startswith(self.redis_handler.elastic_ip_hash_prefix):
                tag_resources[category]['elastic_ip'].append(details)
            elif key.startswith(self.redis_handler.ebs_vol_hash_prefix):
                tag_resources[category]['ebs_volumes'].append(details)
            elif key.startswith(self.redis_handler.ebs_snapshot_hash_prefix):
                tag_resources[category]['ebs_snapshots'].append(details)
            else:
                raise Exception("Unable to categorize info: %s" % str(details))
        ## Calculate total cost
        for category, resources in tag_resources.items():
            for resource_type, resource_list in resources.items():
                total_cost = 0.0
                for details in resource_list:
                    try:
                        total_cost += float(details.get('monthly_cost'))
                    except (ValueError, TypeError):
                        total_cost = 'Undefined'
                if isinstance(total_cost, float):
                    tcost_key = "%s:total_cost" % resource_type
                    tag_resources[category][tcost_key] = round(total_cost, 3)
        return tag_resources


    def get_instance_details(self, region, instance_id):
        details = self.redis_handler.get_instance_details(region, instance_id)
        details = self._cal_monthly_cost(details)
        return details


    def get_ebs_volume_details(self, region, volume_id):
        return self.redis_handler.get_ebs_volume_details(region, volume_id)


    def get_ebs_snapshot_details(self, region, snapshot_id):
        return self.redis_handler.get_ebs_snapshot_details(region, snapshot_id)


    def get_elb_details(self, region, elb_name):
        details = self.redis_handler.get_elb_details(region, elb_name)
        details = self._cal_monthly_cost(details)
        return details


    def get_elastic_ip_details(self, elastic_ip):
        details = self.redis_handler.get_elastic_ip_details(elastic_ip)
        details = self._cal_monthly_cost(details)
        return details


    def _cal_monthly_cost(self, details):
        try:
            if ('per_hour_cost' in details) and ('monthly_cost' not in details):
                ph_cost = float(details.get('per_hour_cost'))
                day_count = get_current_month_day_count()
                details['monthly_cost'] = ph_cost * 24 * day_count
            if 'monthly_cost' in details:
                details['monthly_cost'] = round(float(details['monthly_cost']), 3)
        except ValueError:
            return details
        return details
