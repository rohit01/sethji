# -*- coding: utf-8 -
#

import gevent
import gevent.monkey
gevent.monkey.patch_all()

from sethji import app, ALL_RESOURCE_INDEX
from redis_handler import RedisHandler
from ec2 import get_region_list, Ec2Handler
from aws_pricing_api import AwsPricingApi
import time


class SyncAws(object):
    def __init__(self):
        self.index_keys = None
        self.redis_handler = RedisHandler(
            host=app.config.get('REDIS_HOST'),
            port=app.config.get('REDIS_PORT_NO'),
            password=app.config.get('REDIS_PASSWORD'),
            idle_timeout=app.config.get('REDIS_IDLE_TIMEOUT'),
        )
        self.pricing_api = AwsPricingApi()
        # AWS details
        self.apikey = app.config.get('AWS_ACCESS_KEY_ID')
        self.apisecret = app.config.get('AWS_SECRET_ACCESS_KEY')
        self.owner_id = app.config.get('AWS_OWNER_ID')
        self.regions = app.config.get('REGIONS')
        # Timeout
        self.expire = app.config.get('EXPIRE_DURATION')
        self.sync_timeout = app.config.get('SYNC_TIMEOUT')


    def background_sync(self):
        gevent.spawn_raw(self.sync)


    def get_last_sync_time(self):
        last_sync_time = self.redis_handler.get_last_sync_time()
        if last_sync_time:
            return int(last_sync_time)
        return 0


    def sync(self):
        sync_lock = self.redis_handler.get_sync_lock()
        if sync_lock:
            return
        self.redis_handler.set_sync_lock(timeout=self.sync_timeout)
        self.index_keys = []
        thread_list = self.sync_ec2()
        print 'Sync Started... . . .  .  .   .     .     .'
        gevent.joinall(thread_list, timeout=self.sync_timeout)
        gevent.killall(thread_list)
        print 'Details saved. Indexing records!'
        self.index_records()
        self.redis_handler.set_last_sync_time()
        print 'Starting cleanup of stale records...'
        self.redis_handler.cleanup_keys(self.index_keys)
        self.redis_handler.set_sync_lock(timeout=0)
        print 'Complete'


    def is_sync_in_progress(self):
        sync_lock = self.redis_handler.get_sync_lock()
        if sync_lock:
            return True
        return False


    def sync_ec2(self):
        if (self.regions is None) or (self.regions == 'all'):
            region_list = get_region_list()
        else:
            region_list = [r.strip() for r in self.regions.split(',')]
        thread_list = []
        for region in region_list:
            thread = gevent.spawn(self.sync_ec2_instances, region)
            thread_list.append(thread)
            thread = gevent.spawn(self.sync_ebs_volumes, region)
            thread_list.append(thread)
            thread = gevent.spawn(self.sync_ebs_snapshots, region)
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
            if instance_details.get('state') == 'running':
                per_hr_cost = self.pricing_api.get_instance_per_hr_cost(
                    region, instance_details.get('instance_type'),
                    instance_details.get('platform'))
                instance_details['per_hour_cost'] = per_hr_cost
            else:
                instance_details['per_hour_cost'] = 0.0
            instance_details['timestamp'] = int(time.time())
            if instance_details.get('ebs_ids'):
                for volume_id in instance_details.get('ebs_ids').split(','):
                    ebs_details = self.redis_handler.get_ebs_volume_details(
                        region, volume_id)
                    if not ebs_details:
                        continue
                    ebs_details['instance_id'] = instance_details.get('instance_id')
                    if not instance_details.get('tag_keys'):
                        continue
                    tag_keys = set(instance_details.get('tag_keys').split(','))
                    if ebs_details.get('tag_keys'):
                        tag_keys.update(set(ebs_details.get('tag_keys').split(',')))
                    ebs_details['tag_keys'] = ','.join(tag_keys)
                    for tag_name in instance_details.get('tag_keys').split(','):
                        tag_value = set(instance_details.get('tag:%s' % tag_name, '').split(','))
                        if ebs_details.get('tag:%s' % tag_name, '').strip():
                            old_value = set(ebs_details.get('tag:%s' % tag_name).split(','))
                            tag_value.update(old_value)
                        if not tag_value:
                            continue
                        ebs_details['tag:%s' % tag_name] = ','.join(tag_value)
                    self.redis_handler.save_ebs_vol_details(ebs_details)
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
            per_hr_cost = self.pricing_api.get_elb_per_hr_cost(region)
            details['per_hour_cost'] = per_hr_cost
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
                ## Add Instance tags in elb details
                i_details = self.redis_handler.get_instance_details(
                    details.get('region'), instance_id)
                if i_details.get('tag_keys'):
                    tag_keys = set(i_details.get('tag_keys').split(','))
                    if details.get('tag_keys'):
                        old_keys = set(details.get('tag_keys').split(','))
                        tag_keys.update(old_keys)
                    details['tag_keys'] = ','.join(tag_keys)
                    for tag_name in i_details['tag_keys'].split(','):
                        tag_value = i_details.get('tag:%s' % tag_name, '').strip()
                        if not tag_value:
                            continue
                        tag_value = set(tag_value.split(','))
                        if details.get('tag:%s' % tag_name):
                            old_value = set(details.get('tag:%s' % tag_name).split(','))
                            tag_value.update(old_value)
                        details['tag:%s' % tag_name] = ','.join(tag_value)
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
            details = ec2_handler.get_elastic_ip_details(elastic_ip)
            details['timestamp'] = int(time.time())
            if details.get('instance_id'):
                details['per_hour_cost'] = 0.0
                ## Add Instance tags in Elastic IP details
                i_details = self.redis_handler.get_instance_details(
                    region, details.get('instance_id'))
                if i_details.get('tag_keys'):
                    details['tag_keys'] = i_details.get('tag_keys')
                    for tag_name in i_details['tag_keys'].split(','):
                        tag_value = i_details.get('tag:%s' % tag_name, '').strip()
                        if not tag_value:
                            continue
                        details['tag:%s' % tag_name] = tag_value
            else:
                per_hr_cost = self.pricing_api.get_elastic_ip_per_hr_cost(region)
                details['per_hour_cost'] = per_hr_cost
            hash_key, _ = self.redis_handler.save_elastic_ip_details(details)
            self.index_keys.append(hash_key)
            if self.expire > 0:
                self.redis_handler.expire(hash_key, self.expire)
        print "Elastic ip sync complete for ec2 region: %s" % region


    def sync_ebs_volumes(self, region):
        ec2_handler = Ec2Handler(self.apikey, self.apisecret, region)
        try:
            ebs_volume_list = ec2_handler.fetch_ebs_volumes()
        except Exception as e:
            print "Exception for EBS Volumes in Region: %s, message: %s" \
                  % (region, e.message)
            return
        for ebs_volume in ebs_volume_list:
            details = ec2_handler.get_ebs_details(ebs_volume)
            per_gbm_cost = self.pricing_api.get_ebs_volume_cost(
                region, details.get('type'), 'per_gbm')
            if details.get('type') == 'standard':
                per_mior_cost = self.pricing_api.get_ebs_volume_cost(
                    region, details.get('type'), 'per_mior')
                io_cost = "variable"
                details['per_mior_cost'] = per_mior_cost
            elif details.get('type') == 'gp2':
                io_cost = 0.0
            elif details.get('type') == 'io1':
                per_iops_cost = self.pricing_api.get_ebs_volume_cost(
                    region, details.get('type'), 'per_iops')
                iops_count = details.get('iops', 0)
                if iops_count and per_iops_cost:
                    io_cost = iops_count * per_iops_cost
                else:
                    io_cost = 'Not Found'
                details['per_iops_cost'] = per_iops_cost
            details['per_gbm_storage_cost'] = per_gbm_cost
            monthly_cost = per_gbm_cost * details.get('size')
            if isinstance(io_cost, int) or isinstance(io_cost, float):
                monthly_cost += io_cost
            details['monthly_cost'] = monthly_cost
            details['timestamp'] = int(time.time())
            hash_key, _ = self.redis_handler.save_ebs_vol_details(details)
            self.index_keys.append(hash_key)
            if self.expire > 0:
                self.redis_handler.expire(hash_key, self.expire)
        print "EBS volume sync complete for ec2 region: %s" % region


    def sync_ebs_snapshots(self, region):
        if not self.owner_id:
            return
        ec2_handler = Ec2Handler(self.apikey, self.apisecret, region)
        try:
            ebs_snapshot_list = ec2_handler.fetch_ebs_snapshots(
                owner_id=self.owner_id)
        except Exception as e:
            print "Exception for EBS Snapshots in Region: %s, message: %s" \
                  % (region, e.message)
            return
        for snapshot in ebs_snapshot_list:
            details = ec2_handler.get_snapshot_details(snapshot)
            per_gbm_cost = self.pricing_api.get_ebs_volume_cost(
                region, 'ebs-snapshot', 'per_gbm_stored')
            details['per_gbm_storage_cost'] = per_gbm_cost
            max_monthly_cost = per_gbm_cost * details.get('volume_size')
            details['monthly_cost'] = 'Variable. Depends on actual data stored'
            details['timestamp'] = int(time.time())
            ## Map parent volume tags with snapshot
            ebs_details = self.redis_handler.get_ebs_volume_details(
                    region, details.get('parent_volume_id'))
            if ebs_details:
                if ebs_details.get('instance_id'):
                    details['instance_id'] = ebs_details.get('instance_id')
                if ebs_details.get('tag_keys'):
                    tag_keys = set(ebs_details.get('tag_keys').split(','))
                    if details.get('tag_keys'):
                        tag_keys.update(set(details.get('tag_keys').split(',')))
                    details['tag_keys'] = ','.join(tag_keys)
                    for tag_name in ebs_details.get('tag_keys').split(','):
                        tag_value = set(ebs_details.get('tag:%s' % tag_name, '').split(','))
                        if details.get('tag:%s' % tag_name, '').strip():
                            old_value = set(details.get('tag:%s' % tag_name).split(','))
                            tag_value.update(old_value)
                        if not tag_value:
                            continue
                        details['tag:%s' % tag_name] = ','.join(tag_value)
            ## Save data
            hash_key, _ = self.redis_handler.save_ebs_snapshot_details(details)
            self.index_keys.append(hash_key)
            if self.expire > 0:
                self.redis_handler.expire(hash_key, self.expire)
        print "EBS snapshot sync complete for ec2 region: %s" % region


    def index_records(self):
        indexed_tags = {}
        self.save_index(','.join(self.index_keys), ALL_RESOURCE_INDEX)
        for hash_key in self.index_keys:
            details = self.redis_handler.get_details(hash_key)
            tag_keys = details.get('tag_keys', '').split(',')
            if '' in tag_keys:
                tag_keys.remove('')
            for tag_name in tag_keys:
                tag_value = details.get('tag:%s' % tag_name, '').strip()
                if not tag_value:
                    continue
                tag_value = "%s:%s" % (tag_name, tag_value)
                self.save_index(hash_key, tag_value)
                if ',' in tag_value:
                    for sub_values in tag_value.split(','):
                        self.save_index(hash_key, sub_values)
                if indexed_tags.get(tag_name, None):
                    value_list = indexed_tags[tag_name].split(',')
                    value_list.append(tag_value)
                    indexed_tags[tag_name] = ','.join(set(value_list))
                else:
                    indexed_tags[tag_name] = tag_value
        if indexed_tags:
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
