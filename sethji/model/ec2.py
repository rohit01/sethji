import boto.ec2
import boto.ec2.elb
import sethji.util as util


def get_region_list():
    regions = boto.ec2.get_regions('ec2')
    return [r.name for r in regions]


class Ec2Handler(object):
    def __init__(self, apikey, apisecret, region):
        self.region = region
        self.connection = boto.ec2.connect_to_region(
            region_name=self.region,
            aws_access_key_id=apikey,
            aws_secret_access_key=apisecret
        )
        self.elb_connection = boto.ec2.elb.connect_to_region(
            region_name=self.region,
            aws_access_key_id=apikey,
            aws_secret_access_key=apisecret
        )


    def fetch_all_instances(self):
        reservations = self.connection.get_all_instances()
        instance_list = []
        for r in reservations:
            for i in r.instances:
                instance_list.append(i)
        return instance_list


    def get_instance_details(self, instance):
        details = {}
        details['instance_id'] = instance.id
        details['region'] = instance.region.name
        details['zone'] = instance.placement
        details['instance_type'] = instance.instance_type
        details['private_ip_address'] = instance.private_ip_address
        details['ip_address'] = instance.ip_address
        details['ec2_dns'] = instance.dns_name
        details['ec2_private_dns'] = instance.private_dns_name
        details['state'] = instance.state
        details['architecture'] = instance.architecture
        details['launch_time'] = instance.launch_time
        details['ebs_optimized'] = instance.ebs_optimized
        details['vpc_id'] = instance.vpc_id
        details['root_device_type'] = instance.root_device_type
        details['platform'] = instance.platform or 'linux'
        for _, volume in instance.block_device_mapping.items():
            if not volume.volume_id:
                continue
            if details.get('ebs_ids'):
                details['ebs_ids'] = "%s,%s" % (details.get('ebs_ids'),
                                                volume.volume_id)
            else:
                details['ebs_ids'] = volume.volume_id
        tag_keys = []
        for k, v in instance.tags.items():
            k, v = k.strip(), v.strip()
            if (not k) or (not v):
                continue
            details['tag:%s' % k] = v
            tag_keys.append(k)
        if tag_keys:
            details['tag_keys'] = ','.join(tag_keys)
        details = util.convert_none_into_blank_values(details)
        return details


    def fetch_all_elbs(self):
        return self.elb_connection.get_all_load_balancers()


    def get_elb_details(self, elb):
        ## Get instances with health info
        instance_details = {}
        instance_health = elb.get_instance_health()
        for instance in instance_health:
            instance_details[instance.instance_id] = instance.state
        ## Map details
        details = {}
        details['elb_name'] = elb.name
        details['region'] = elb.connection.region.name
        details['elb_dns'] = elb.dns_name
        details['vpc_id'] = elb.vpc_id
        details['created_time'] = elb.created_time
        details['subnets'] = ','.join(elb.subnets)
        details['elb_instances'] = ','.join(['%s %s' % (k, v)
                                         for k, v in instance_details.items()])
        details = util.convert_none_into_blank_values(details)
        return details, instance_details.keys()


    def fetch_elastic_ips(self):
        return self.connection.get_all_addresses()


    def get_elastic_ip_details(self, elastic_ip):
        details = {
            'elastic_ip': elastic_ip.public_ip,
            'instance_id': elastic_ip.instance_id,
            'region': elastic_ip.region.name,
        }
        return util.convert_none_into_blank_values(details)


    def fetch_ebs_volumes(self):
        return self.connection.get_all_volumes()


    def get_ebs_details(self, ebs):
        details = {
            'create_time': ebs.create_time,
            'volume_id': ebs.id,
            'iops': ebs.iops,
            'region': ebs.region.name,
            'size': ebs.size,
            'parent_snapshot_id': ebs.snapshot_id,
            'status': ebs.status,
            'type': ebs.type,
            'zone': ebs.zone,
        }
        tag_keys = []
        for k, v in ebs.tags.items():
            k, v = k.strip(), v.strip()
            if (not k) or (not v):
                continue
            details['tag:%s' % k] = v
            tag_keys.append(k)
        if tag_keys:
            details['tag_keys'] = ','.join(tag_keys)
        return util.convert_none_into_blank_values(details)


    def fetch_ebs_snapshots(self, owner_id):
        return self.connection.get_all_snapshots(owner=owner_id)


    def get_snapshot_details(self, snapshot):
        details = {
            'owner_alias': snapshot.owner_alias,
            'owner_id': snapshot.owner_id,
            'start_time': snapshot.start_time,
            'description': snapshot.description,
            'snapshot_id': snapshot.id,
            'progress': snapshot.progress,
            'status': snapshot.status,
            'parent_volume_id': snapshot.volume_id,
            'encrypted': snapshot.encrypted,
            'volume_size': snapshot.volume_size,
            'region': snapshot.region.name,
        }
        tag_keys = []
        for k, v in snapshot.tags.items():
            k, v = k.strip(), v.strip()
            if (not k) or (not v):
                continue
            details['tag:%s' % k] = v
            tag_keys.append(k)
        if tag_keys:
            details['tag_keys'] = ','.join(tag_keys)
        return util.convert_none_into_blank_values(details)
