# -*- coding: utf-8 -
#

import redis
import time


class RedisHandler(object):
    def __init__(self, host=None, port=None, password=None, timeout=None):
        if host is None:
            host = '127.0.0.1'
        if port is None:
            port = 6379
        self.connection = redis.Redis(host=host, port=port, password=password,
            socket_timeout=timeout)
        self.instance_hash_prefix = 'aws:ec2:instance'          ## Suffix: region, instance id
        self.ebs_vol_hash_prefix = 'aws:ec2:ebs'                ## Suffix: region, volume id
        self.elb_hash_prefix = 'aws:ec2:elb'                    ## Suffix: region, elb name
        self.elastic_ip_hash_prefix = 'aws:ec2:elastic_ip'      ## Suffix: ip_address
        self.index_prefix = 'aws:index'                         ## Suffix: index_item
        self.all_tags_hash = 'sethji:indexed_tags'              ## No Suffix
        self.sync_lock_hash = 'sethji:sync_lock'                ## No Suffix
        self.last_sync_time_hash = 'sethji:last_sync_time'      ## No Suffix
        self.object_cache_hash = 'sethji:object_cache'          ## object path


    def get_cached_object(self, path):
        hash_key = "%s:%s" % (self.object_cache_hash, path)
        return self.connection.get(hash_key)


    def set_object_cache(self, path, content, expire_duration):
        hash_key = "%s:%s" % (self.object_cache_hash, path)
        self.connection.set(hash_key, content)
        if expire_duration:
            self.connection.expire(hash_key, expire_duration)


    def flush_object_cache(self):
        for hash_key in self.connection.keys("%s*" % self.object_cache_hash):
            self.connection.delete(hash_key)


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


    def clean_instance_entries(self, valid_keys):
        hash_list = self.connection.keys("%s*" % self.instance_hash_prefix)
        if hash_list:
            self.connection.delete(*hash_list)


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


    def save_indexed_tags(self, indexed_tags):
        status = self.connection.hmset(self.all_tags_hash, indexed_tags)
        return (self.all_tags_hash, status)


    def get_indexed_tags(self):
        return self.connection.hgetall(self.all_tags_hash)


    def clean_elb_entries(self, valid_keys):
        hash_list = self.connection.keys("%s*" % self.elb_hash_prefix)
        if hash_list:
            self.connection.delete(*hash_list)


    def save_elastic_ip_details(self, item_details):
        hash_key = "%s:%s" % (self.elastic_ip_hash_prefix,
                              item_details['elastic_ip'])
        status = self.connection.hmset(hash_key, item_details)
        return (hash_key, status)


    def clean_elastic_ip_entries(self, valid_keys):
        hash_list = self.connection.keys("%s*" % self.elastic_ip_hash_prefix)
        if hash_list:
            self.connection.delete(*hash_list)


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
