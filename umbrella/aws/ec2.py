import boto.ec2
import boto.ec2.elb
import umbrella.util as util

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
        tag_keys = []
        for k, v in instance.tags.items():
            k, v = k.strip(), v.strip()
            details['tag:%s' % k] = v
            tag_keys.append(k)
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
        details['elb_instances'] = ','.join(['%s %s' % (k, v)
                                         for k, v in instance_details.items()])
        details = util.convert_none_into_blank_values(details)
        return details, instance_details.keys()

    def fetch_elastic_ips(self):
        return self.connection.get_all_addresses()

    def get_elastic_ip_detail(self, elastic_ip):
        details = {
            'elastic_ip': elastic_ip.public_ip,
            'instance_id': elastic_ip.instance_id,
        }
        return util.convert_none_into_blank_values(details)
