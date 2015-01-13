# -*- coding: utf-8 -
#

import gevent
import gevent.monkey
gevent.monkey.patch_all()

import redis
import time


connection_pool = None


class RedisHandler(object):
    def __init__(self, host=None, port=None, password=None, idle_timeout=None):
        global connection_pool
        if host is None:
            host = '127.0.0.1'
        if port is None:
            port = 6379
        if not connection_pool:
            connection_pool = redis.ConnectionPool(host=host, port=port,
                                                   password=password)
        self.connection = redis.StrictRedis(connection_pool=connection_pool)
        self.idle_timeout = idle_timeout
        self.instance_hash_prefix = 'aws:ec2:instance'          ## Suffix: region, instance id
        self.ebs_vol_hash_prefix = 'aws:ec2:ebs:vol'            ## Suffix: region, volume id
        self.ebs_snapshot_hash_prefix = 'aws:ec2:ebs:snap'      ## Suffix: region, snapshot id
        self.elb_hash_prefix = 'aws:ec2:elb'                    ## Suffix: region, elb name
        self.elastic_ip_hash_prefix = 'aws:ec2:elastic_ip'      ## Suffix: ip_address
        self.index_prefix = 'aws:index'                         ## Suffix: index_item
        self.all_tags_hash = 'sethji:indexed_tags'              ## No Suffix
        self.sync_lock_hash = 'sethji:sync_lock'                ## No Suffix
        self.last_sync_time_hash = 'sethji:last_sync_time'      ## No Suffix
        self.object_cache_hash = 'sethji:object_cache'          ## object path
        gevent.spawn_raw(self._close_idle_connections)


    def get_cached_object(self, path):
        hash_key = "%s:%s" % (self.object_cache_hash, path)
        return self.connection.get(hash_key)


    def set_object_cache(self, path, content, expire_duration):
        hash_key = "%s:%s" % (self.object_cache_hash, path)
        self.connection.set(hash_key, content)
        if expire_duration:
            self.connection.expire(hash_key, expire_duration)


    def set_last_sync_time(self):
        time_now = int(round(time.time()))
        return self.connection.set(self.last_sync_time_hash, time_now)


    def get_last_sync_time(self):
        return self.connection.get(self.last_sync_time_hash)


    def set_sync_lock(self, timeout=None):
        if (not timeout) or (timeout <= 0):
            return self.connection.delete(self.sync_lock_hash)
        time_now = int(round(time.time()))
        return self.connection.set(self.sync_lock_hash, time_now, ex=timeout)


    def get_sync_lock(self):
        return self.connection.get(self.sync_lock_hash)


    def save_instance_details(self, item_details):
        hash_key = "%s:%s:%s" % (self.instance_hash_prefix,
                                 item_details['region'],
                                 item_details['instance_id'])
        status = self.connection.hmset(hash_key, item_details)
        return (hash_key, status)


    def get_instance_details(self, region, instance_id):
        hash_key = "%s:%s:%s" % (self.instance_hash_prefix, region, instance_id)
        return self.connection.hgetall(hash_key)


    def get_elastic_ip_details(self, elastic_ip):
        hash_key = "%s:%s" % (self.elastic_ip_hash_prefix, elastic_ip)
        return self.connection.hgetall(hash_key)


    def add_instance_detail(self, region, instance_id, key, value):
        hash_key = "%s:%s:%s" % (self.instance_hash_prefix, region,
                                 instance_id)
        status = self.connection.hset(hash_key, key, value)
        return (hash_key, status)


    def get_instance_item_value(self, region, instance_id, key):
        hash_key = "%s:%s:%s" % (self.instance_hash_prefix, region,
                                 instance_id)
        return self.connection.hget(hash_key, key)


    def save_elb_details(self, item_details):
        hash_key = "%s:%s:%s" % (self.elb_hash_prefix,
                                 item_details['region'],
                                 item_details['elb_name'])
        status = self.connection.hmset(hash_key, item_details)
        return (hash_key, status)


    def get_elb_details(self, region, elb_name):
        hash_key = "%s:%s:%s" % (self.elb_hash_prefix, region, elb_name)
        return self.connection.hgetall(hash_key)


    def save_ebs_vol_details(self, item_details):
        hash_key = "%s:%s:%s" % (self.ebs_vol_hash_prefix,
                                 item_details['region'],
                                 item_details['volume_id'])
        status = self.connection.hmset(hash_key, item_details)
        return (hash_key, status)


    def get_ebs_volume_details(self, region, volume_id):
        hash_key = "%s:%s:%s" % (self.ebs_vol_hash_prefix, region, volume_id)
        return self.connection.hgetall(hash_key)


    def save_ebs_snapshot_details(self, item_details):
        hash_key = "%s:%s:%s" % (self.ebs_snapshot_hash_prefix,
                                 item_details['region'],
                                 item_details['snapshot_id'])
        status = self.connection.hmset(hash_key, item_details)
        return (hash_key, status)


    def get_ebs_snapshot_details(self, region, snapshot_id):
        hash_key = "%s:%s:%s" % (self.ebs_snapshot_hash_prefix, region,
                                 snapshot_id)
        return self.connection.hgetall(hash_key)


    def save_indexed_tags(self, indexed_tags):
        status = self.connection.hmset(self.all_tags_hash, indexed_tags)
        return (self.all_tags_hash, status)


    def get_indexed_tags(self):
        return self.connection.hgetall(self.all_tags_hash)


    def save_elastic_ip_details(self, item_details):
        hash_key = "%s:%s" % (self.elastic_ip_hash_prefix,
                              item_details['elastic_ip'])
        status = self.connection.hmset(hash_key, item_details)
        return (hash_key, status)


    def get_details(self, hash_key):
        return self.connection.hgetall(hash_key)


    def save_index(self, key, value):
        hash_key = "%s:%s" % (self.index_prefix, key)
        status = self.connection.set(hash_key, value)
        return (hash_key, status)


    def expire_index(self, key, duration):
        hash_key = "%s:%s" % (self.index_prefix, key)
        return self.connection.expire(hash_key, duration)


    def get_index(self, key):
        hash_key = "%s:%s" % (self.index_prefix, key)
        return self.connection.get(hash_key)


    def exists(self, hash_key):
        return self.connection.exists(hash_key)


    def expire(self, hash_key, duration):
        return self.connection.expire(hash_key, duration)


    def cleanup_keys(self, valid_keys):
        hash_set = set([])
        hash_set.update(self.connection.keys("%s*" % self.instance_hash_prefix) or [])
        hash_set.update(self.connection.keys("%s*" % self.ebs_vol_hash_prefix) or [])
        hash_set.update(self.connection.keys("%s*" % self.ebs_snapshot_hash_prefix) or [])
        hash_set.update(self.connection.keys("%s*" % self.elb_hash_prefix) or [])
        hash_set.update(self.connection.keys("%s*" % self.elastic_ip_hash_prefix) or [])
        hash_set.update(self.connection.keys("%s*" % self.object_cache_hash) or [])
        hash_set.difference_update(set(valid_keys))
        if hash_set:
            self.connection.delete(*hash_set)


    def _close_idle_connections(self):
        client_list = self.connection.client_list()
        idle_connection_mapping = {}
        for client in client_list:
            idle_connection_mapping[int(client['idle'])] = client['addr']
        idle_time_list = idle_connection_mapping.keys()
        idle_time_list.sort(reverse=True)
        for idle_time in idle_time_list:
            if idle_time < self.idle_timeout:
                break
            try:
                self.connection.client_kill(idle_connection_mapping[idle_time])
            except Exception as e:
                print "Exception while closing idle redis connection. " \
                    "Message: %s" % str(e.message)
