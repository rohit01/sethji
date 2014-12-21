# -*- coding: utf-8 -
#

import gevent
import gevent.monkey
gevent.monkey.patch_all()

from umbrella import app
from redis_handler import RedisHandler
from ec2 import get_region_list, Ec2Handler
import time


class SyncAws(object):
    def __init__(self):
        self.index_keys = None
        self.redis_handler = RedisHandler(
            host=app.config.get('REDIS_HOST'),
            port=app.config.get('REDIS_PORT_NO'),
            password=app.config.get('REDIS_PASSWORD'),
            timeout=app.config.get('REDIS_TIMEOUT'),
        )
        # AWS details
        self.apikey = app.config.get('AWS_ACCESS_KEY_ID')
        self.apisecret = app.config.get('AWS_SECRET_ACCESS_KEY')
        self.regions = app.config.get('REGIONS')
        # Timeout
        self.expire = app.config.get('EXPIRE_DURATION')
        self.sync_timeout = app.config.get('SYNC_TIMEOUT')


    def sync(self):
        self.index_keys = []
        thread_list = self.sync_ec2()
        print 'Sync Started... . . .  .  .   .     .     .'
        gevent.joinall(thread_list, timeout=self.sync_timeout)
        gevent.killall(thread_list)
        print 'Starting cleanup of stale records...'
        self.clean_stale_entries()
        print 'Details saved. Indexing records!'
        self.index_records()
        print 'Complete'

    def sync_ec2(self):
        if (self.regions is None) or (self.regions == 'all'):
            region_list = get_region_list()
        else:
            region_list = [r.strip() for r in self.regions.split(',')]
        thread_list = []
        for region in region_list:
            thread = gevent.spawn(self.sync_ec2_instances, region)
            thread_list.append(thread)
            thread = gevent.spawn(self.sync_ec2_elbs, region)
            thread_list.append(thread)
            thread = gevent.spawn(self.sync_elastic_ips, region)
            thread_list.append(thread)
        return thread_list

    def sync_ec2_instances(self, region):
        ec2_handler = Ec2Handler(self.apikey, self.apisecret, region)
        try:
            instance_list = ec2_handler.fetch_all_instances()
        except Exception as e:
            print "Exception for EC2 in Region: %s, message: %s" \
                % (region, e.message)
            return
        for instance in instance_list:
            instance_details = ec2_handler.get_instance_details(instance)
            instance_details['timestamp'] = int(time.time())
            hash_key, _ = self.redis_handler.save_instance_details(
                instance_details)
            self.index_keys.append(hash_key)
            if self.expire > 0:
                self.redis_handler.expire(hash_key, self.expire)
        print "Instance sync complete for ec2 region: %s" % region

    def sync_ec2_elbs(self, region):
        ec2_handler = Ec2Handler(self.apikey, self.apisecret, region)
        try:
            elb_list = ec2_handler.fetch_all_elbs()
        except Exception as e:
            print "Exception for ELB in Region: %s, message: %s" % (region,
                                                                    e.message)
            return
        for elb in elb_list:
            details, instance_id_list = ec2_handler.get_elb_details(elb)
            details['timestamp'] = int(time.time())
            for instance_id in instance_id_list:
                instance_elb_names = self.redis_handler.get_instance_item_value(
                    region=details.get('region'),
                    instance_id=instance_id,
                    key='instance_elb_names'
                ) or ''
                instance_elb_names = set(instance_elb_names.split(','))
                if '' in instance_elb_names:
                    instance_elb_names.remove('')
                instance_elb_names.add(elb.name)
                instance_elb_names = ','.join(instance_elb_names)
                self.redis_handler.add_instance_detail(
                    region=details.get('region'),
                    instance_id=instance_id,
                    key='instance_elb_names',
                    value=instance_elb_names,
                )
            hash_key, _ = self.redis_handler.save_elb_details(details)
            self.index_keys.append(hash_key)
            if self.expire > 0:
                self.redis_handler.expire(hash_key, self.expire)
        print "ELB sync complete for ec2 region: %s" % region


    def sync_elastic_ips(self, region):
        ec2_handler = Ec2Handler(self.apikey, self.apisecret, region)
        try:
            elastic_ip_list = ec2_handler.fetch_elastic_ips()
        except Exception as e:
            print "Exception for Elastic IPs in Region: %s, message: %s" \
                  % (region, e.message)
            return
        for elastic_ip in elastic_ip_list:
            details = ec2_handler.get_elastic_ip_detail(elastic_ip)
            details['timestamp'] = int(time.time())
            hash_key, _ = self.redis_handler.save_elastic_ip_details(details)
            self.index_keys.append(hash_key)
            if self.expire > 0:
                self.redis_handler.expire(hash_key, self.expire)
        print "Elastic ip sync complete for ec2 region: %s" % region


    def clean_stale_entries(self):
        self.redis_handler.clean_instance_entries(valid_keys=self.index_keys)
        self.redis_handler.clean_elb_entries(valid_keys=self.index_keys)
        self.redis_handler.clean_elastic_ip_entries(valid_keys=self.index_keys)


    def index_records(self):
        indexed_tags = {}
        default_tag = "--UNTAGGED--"
        for hash_key in self.index_keys:
            details = self.redis_handler.get_details(hash_key)
            tag_keys = details.get('tag_keys', '').split(',')
            if '' in tag_keys:
                tag_keys.remove('')
            if not tag_keys:
                tag_keys = [default_tag]
            for tage_name in tag_keys:
                if tage_name == default_tag:
                    tag_value = default_tag
                else:
                    tag_value = details['tag:%s' % tage_name].strip()
                self.save_index(hash_key, tag_value)
                if indexed_tags.get(tage_name, None):
                    value_list = indexed_tags[tage_name].split(',')
                    value_list.append(tag_value)
                    indexed_tags[tage_name] = ','.join(set(value_list))
                else:
                    indexed_tags[tage_name] = tag_value
        self.redis_handler.save_indexed_tags(indexed_tags)


    def save_index(self, hash_key, value):
        index_value = self.redis_handler.get_index(value)
        if index_value:
            index_value = "%s,%s" % (index_value, hash_key)
        else:
            index_value = hash_key
        ## Remove redundant values
        indexed_keys = set(index_value.split(','))
        ## Clean stale index entries
        for k in indexed_keys.copy():
            if not self.redis_handler.exists(k):
                indexed_keys.remove(k)
        ## Save Index
        if len(indexed_keys) > 0:
            self.redis_handler.save_index(value, ','.join(indexed_keys))
            self.redis_handler.expire_index(value, self.expire)
