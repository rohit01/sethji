import os

## Set as true to run on debug mode
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

## AWS Credentials
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

## Redis settings
REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
REDIS_PORT_NO = int(os.environ.get('REDIS_PORT_NO', 6379))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')
REDIS_TIMEOUT = int(os.environ.get('REDIS_TIMEOUT', 2))

## Application host and port
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 5000))

# ## Sync lock settings to prevent Myltiple sync. Setting this as False may
# ## overload the server
# SYNC_LOCK = os.environ.get('SYNC_LOCK', True)
SYNC_TIMEOUT = int(os.environ.get('SYNC_TIMEOUT', 600))
# MIN_SYNC_GAP = int(os.environ.get('MIN_SYNC_GAP', 30))

# ## Route53 hosted zone named separated by comma
# HOSTED_ZONES = 'all'

## EC2 region to be synced (comma separated values)
REGIONS = 'all'

## Redis key expiry settings
EXPIRE_DURATION = 2592000                # 30 Days
# TTL = False

# ## Set as True if you dont want to sync both
# NO_EC2 = False
# NO_ROUTE53 = False

# ## Sentry for catching exceptions
# SENTRY_DSN = os.environ.get('SENTRY_DSN', None)
