import os

## Set as true to run in debug mode
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

## AWS Credentials
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

## Google OAuth Credentials
GOOGLE_ID = os.environ.get('GOOGLE_ID', None)
GOOGLE_SECRET = os.environ.get('GOOGLE_SECRET', None)
AUTHORIZED_EMAILS = os.environ.get('AUTHORIZED_EMAILS', '*')
LOGIN_ENABLED = (GOOGLE_ID is not None) and (GOOGLE_SECRET is not None)

## Redis settings
REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
REDIS_PORT_NO = int(os.environ.get('REDIS_PORT_NO', 6379))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')
REDIS_TIMEOUT = int(os.environ.get('REDIS_TIMEOUT', 2))

## Application host and port
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 5000))

## AWS Sync and auto refresh timeouts
SYNC_TIMEOUT = int(os.environ.get('SYNC_TIMEOUT', 600))
AUTO_REFRESH_TIMEOUT = int(os.environ.get('AUTO_REFRESH_TIMEOUT', 600))

## EC2 region to be synced (comma separated values)
REGIONS = os.environ.get('REGIONS', 'all')

## Duration for which data is cached
EXPIRE_DURATION = 2592000                # 30 Days

## Sentry for catching exceptions
SENTRY_DSN = os.environ.get('SENTRY_DSN', None)

## Secret key for cookies
SECRET_KEY = os.urandom(128)
