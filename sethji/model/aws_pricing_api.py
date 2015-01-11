# -*- coding: utf-8 -
#

import requests
import json
import re


PRICING_URLS = {
    "LINUX_INSTANCE_ON_DEMAND": "http://a0.awsstatic.com/pricing/1/ec2/linux-od.min.js",
    "PG_LINUX_INSTANCE_ON_DEMAND": "http://a0.awsstatic.com/pricing/1/ec2/previous-generation/linux-od.min.js",
    "WINDOWS_INSTANCE_ON_DEMAND": "http://a0.awsstatic.com/pricing/1/ec2/mswin-od.min.js",
    "PG_WINDOWS_INSTANCE_ON_DEMAND": "http://a0.awsstatic.com/pricing/1/ec2/previous-generation/mswin-od.min.js",

    "EBS_VOLUME": "http://a0.awsstatic.com/pricing/1/ebs/pricing-ebs.min.js",
    "ELB": "http://a0.awsstatic.com/pricing/1/elasticloadbalancer/pricing-elb.min.js",
    "ELASTIC_IP": "http://a0.awsstatic.com/pricing/1/ec2/pricing-elastic-ips.min.js",
}

INSTANCE_PLATFORM_TO_RESOURCE_TYPE = {
    "linux": ["LINUX_INSTANCE_ON_DEMAND", "PG_LINUX_INSTANCE_ON_DEMAND"],
    "windows": ["WINDOWS_INSTANCE_ON_DEMAND", "PG_WINDOWS_INSTANCE_ON_DEMAND"],
}

JSON_NAME_TO_EC2_REGIONS_API = {
    "us-east" : "us-east-1",
    "us-west" : "us-west-1",
    "eu-ireland" : "eu-west-1",
    "eu-west" : "eu-west-1",
    "apac-sin" : "ap-southeast-1",
    "ap-southeast" : "ap-southeast-1",
    "apac-syd" : "ap-southeast-2",
    "apac-tokyo" : "ap-northeast-1",
    "ap-northeast" : "ap-northeast-1",
}

JSON_NAME_TO_EC2_EBS_VOL_API = {
    "Amazon EBS General Purpose (SSD) volumes": "gp2",
    "Amazon EBS Provisioned IOPS (SSD) volumes": "io1",
    "Amazon EBS Magnetic volumes": "standard",
    "ebsSnapsToS3": "--not-applicable--",
}


class AwsPricingApi(object):
    """
    Provides programatic access to AWS pricing.
    Supported products:
        * EC2 linux on demand instances
        * EC2 EBS volumes
        * EC2 ELBs
        * EC2 Elastic IPs
    """
    def __init__(self):
        self.max_retries = 3
        self.price_info = {}
        self.currency = 'USD'


    def get_instance_per_hr_cost(self, region, instance_type, platform):
        resource_type_list = INSTANCE_PLATFORM_TO_RESOURCE_TYPE.get(platform, [])
        for resource_type in resource_type_list:
            self._fetch_price_info(resource_type)
            region_price = self._filter_region_price(
                self.price_info.get(resource_type, {}), region)
            if not region_price:
                return None
            price_type_list = region_price.get('instanceTypes', [])
            for price_type in price_type_list:
                price_values = price_type.get('sizes', [])
                for rate_info in price_values:
                    if rate_info.get('size') == instance_type:
                        value = rate_info.get('valueColumns', [{}])[0]
                        return float(value.get('prices', {}).get(self.currency))
        return None


    def get_ebs_volume_per_gb_cost(self, region, ebs_type):
        self._fetch_price_info('EBS_VOLUME')
        region_price = self._filter_region_price(
            self.price_info.get('EBS_VOLUME', {}), region)
        if not region_price:
            return None
        price_type_list = region_price.get('types', [])
        for price_type in price_type_list:
            name = price_type.get('name')
            if not (ebs_type == JSON_NAME_TO_EC2_EBS_VOL_API.get(name, name)):
                continue
            price_values = price_type.get('values', [])
            for rate_info in price_values:
                if rate_info.get('rate') == 'perGBmoProvStorage':
                    return float(rate_info.get('prices', {}).get(self.currency))
        return None


    def get_elb_per_hr_cost(self, region):
        self._fetch_price_info('ELB')
        region_price = self._filter_region_price(
            self.price_info.get('ELB', {}), region)
        if not region_price:
            return None
        price_values = region_price.get('types', [{}])[0].get('values', [])
        for rate_info in price_values:
            if rate_info.get('rate') == 'perELBHour':
                return float(rate_info.get('prices', {}).get(self.currency))
        return None


    def get_elastic_ip_per_hr_cost(self, region):
        self._fetch_price_info('ELASTIC_IP')
        region_price = self._filter_region_price(
            self.price_info.get('ELASTIC_IP', {}), region)
        if not region_price:
            return None
        price_values = region_price.get('types', [{}])[0].get('values', [])
        for rate_info in price_values:
            if rate_info.get('rate') == 'perNonAttachedPerHour':
                return float(rate_info.get('prices', {}).get(self.currency))
        return None


    def _fetch_price_info(self, resource_type):
        if self.price_info.get(resource_type):
            return
        url = PRICING_URLS.get(resource_type)
        if not url:
            raise Exception("Pricing URL not defined for resource type: %s"
                            % resource_type)
        for retry_no in xrange(self.max_retries):
            try:
                resp = requests.get(url, timeout=5)
                if not (200 <= resp.status_code < 300):
                    raise Exception("Status code: %s" % resp.status_code)
                break
            except Exception as e:
                if retry_no < (self.max_retries - 1):
                    continue
                raise Exception("URL: %s. Exception message: %s" 
                                % (url, e.message))
        content = resp.text
        if not content:
            return
        # Remove comment, whitespaces and ;
        while content and (content[0] in [' ', '\t', '\n']):
            content = content[1:]
        if content.startswith('/*'):
            content = content[(content.find('*/')+2):]
        while content and (content[0] in [' ', '\t', '\n']):
            content = content[1:]
        while content and (content[-1] in [' ', '\t', '\n', ';']):
            content = content[:-1]
        # Remove callback string
        if content.startswith('callback('):
            json_str = content[len('callback('):-1]
        else:
            json_str = content
        json_str = re.sub('''([,\{][\s]*)([a-zA-Z0-9_]+)([\s]*:)''',
                          r'\1"\2"\3', json_str)
        self.price_info[resource_type] = json.loads(json_str)


    def _filter_region_price(self, price_info, region):
        for region_price in price_info.get('config', {}).get('regions', []):
            name = region_price.get('region')
            if region == JSON_NAME_TO_EC2_REGIONS_API.get(name, name):
                return region_price
        return None
