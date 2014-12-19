# -*- coding: utf-8 -
#

import gevent
import gevent.monkey
gevent.monkey.patch_all()

import umbrella
import umbrella.config
import umbrella.database.redis_handler
import umbrella.aws.ec2
import redis
import time


index_keys = None


def get_redis_handler():
    return umbrella.database.redis_handler.RedisHandler(
        host=umbrella.config.REDIS_HOST,
        port=umbrella.config.REDIS_PORT_NO,
        password=umbrella.config.REDIS_PASSWORD,
        timeout=umbrella.config.REDIS_TIMEOUT,
    )


def sync_aws():
    global index_keys
    index_keys = []
    thread_list = sync_ec2(
        apikey=umbrella.config.AWS_ACCESS_KEY_ID,
        apisecret=umbrella.config.AWS_SECRET_ACCESS_KEY,
        regions=umbrella.config.REGIONS,
        expire=umbrella.config.EXPIRE_DURATION
    )
    print 'Sync Started... . . .  .  .   .     .     .'
    gevent.joinall(thread_list, timeout=umbrella.config.SYNC_TIMEOUT)
    gevent.killall(thread_list)
    print 'Starting cleanup of stale records...'
    clean_stale_entries()
    print 'Details saved. Indexing records!'
    umbrella.sync.index_records(expire=umbrella.config.EXPIRE_DURATION)
    index_keys = None
    print 'Complete'


def sync_ec2(apikey, apisecret, regions, expire):
    if (regions is None) or (regions == 'all'):
        region_list = umbrella.aws.ec2.get_region_list()
    else:
        region_list = [r.strip() for r in regions.split(',')]
    thread_list = []
    for region in region_list:
        thread = gevent.spawn(sync_ec2_instances, apikey, apisecret, region,
                              expire)
        thread_list.append(thread)
        thread = gevent.spawn(sync_ec2_elbs, apikey, apisecret, region, expire)
        thread_list.append(thread)
        thread = gevent.spawn(sync_elastic_ips, apikey, apisecret, region,
                              expire)
        thread_list.append(thread)
    return thread_list


def sync_ec2_instances(apikey, apisecret, region, expire):
    ec2_handler = umbrella.aws.ec2.Ec2Handler(apikey, apisecret, region)
    redis_handler = get_redis_handler()
    try:
        instance_list = ec2_handler.fetch_all_instances()
    except Exception as e:
        print "Exception for EC2 in Region: %s, message: %s" \
              % (ec2_handler.region, e.message)
        return
    for instance in instance_list:
        instance_details = ec2_handler.get_instance_details(instance)
        instance_details['timestamp'] = int(time.time())
        hash_key, status = redis_handler.save_instance_details(instance_details)
        index_keys.append(hash_key)
        if expire > 0:
            redis_handler.expire(hash_key, expire)
    print "Instance sync complete for ec2 region: %s" % ec2_handler.region


def sync_ec2_elbs(apikey, apisecret, region, expire):
    ec2_handler = umbrella.aws.ec2.Ec2Handler(apikey, apisecret, region)
    redis_handler = get_redis_handler()
    try:
        elb_list = ec2_handler.fetch_all_elbs()
    except Exception as e:
        print "Exception for ELB in Region: %s, message: %s" \
              % (ec2_handler.region, e.message)
        return
    for elb in elb_list:
        details, instance_id_list = ec2_handler.get_elb_details(elb)
        details['timestamp'] = int(time.time())
        for instance_id in instance_id_list:
            instance_elb_names = redis_handler.get_instance_item_value(
                region=details['region'], instance_id=instance_id,
                key='instance_elb_names'
            ) or ''
            instance_elb_names = set(instance_elb_names.split(','))
            if '' in instance_elb_names:
                instance_elb_names.remove('')
            instance_elb_names.add(elb.name)
            instance_elb_names = ','.join(instance_elb_names)
            redis_handler.add_instance_detail(
                region=details['region'], instance_id=instance_id,
                key='instance_elb_names', value=instance_elb_names,
            )
        hash_key, status = redis_handler.save_elb_details(details)
        index_keys.append(hash_key)
        if expire > 0:
            redis_handler.expire(hash_key, expire)
    print "ELB sync complete for ec2 region: %s" % ec2_handler.region


def sync_elastic_ips(apikey, apisecret, region, expire):
    ec2_handler = umbrella.aws.ec2.Ec2Handler(apikey, apisecret, region)
    redis_handler = get_redis_handler()
    try:
        elastic_ip_list = ec2_handler.fetch_elastic_ips()
    except Exception as e:
        print "Exception for Elastic IPs in Region: %s, message: %s" \
              % (ec2_handler.region, e.message)
        return
    for elastic_ip in elastic_ip_list:
        details = ec2_handler.get_elastic_ip_detail(elastic_ip)
        details['timestamp'] = int(time.time())
        hash_key, status = redis_handler.save_elastic_ip_details(details)
        index_keys.append(hash_key)
        if expire > 0:
            redis_handler.expire(hash_key, expire)
    print "Elastic ip sync complete for ec2 region: %s" % ec2_handler.region


def clean_stale_entries():
    redis_handler = get_redis_handler()
    redis_handler.clean_instance_entries(valid_keys=index_keys)
    redis_handler.clean_elb_entries(valid_keys=index_keys)
    redis_handler.clean_elastic_ip_entries(valid_keys=index_keys)


def index_records(expire):
    redis_handler = get_redis_handler()
    indexed_tags = {}
    default_tag = "--UNTAGGED--"
    for hash_key in index_keys:
        details = redis_handler.get_details(hash_key)
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
            save_index(hash_key, tag_value, expire)
            if indexed_tags.get(tage_name, None):
                value_list = indexed_tags[tage_name].split(',')
                value_list.append(tag_value)
                indexed_tags[tage_name] = ','.join(set(value_list))
            else:
                indexed_tags[tage_name] = tag_value
    redis_handler.save_indexed_tags(indexed_tags)


def save_index(hash_key, value, expire):
    redis_handler = get_redis_handler()
    index_value = redis_handler.get_index(value)
    if index_value:
        index_value = "%s,%s" % (index_value, hash_key)
    else:
        index_value = hash_key
    ## Remove redundant values
    indexed_keys = set(index_value.split(','))
    ## Clean stale entries
    for k in indexed_keys.copy():
        if not redis_handler.exists(k):
            indexed_keys.remove(k)
    ## Save Index
    if len(indexed_keys) > 0:
        redis_handler.save_index(value, ','.join(indexed_keys))
    else:
        redis_handler.delete_index(value)
    redis_handler.expire_index(value, expire)
