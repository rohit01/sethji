#!/usr/bin/env bash
#
# Install script to deploy sethji as a heroku application
# Author - @rohit01

echo -e "Input heroku application name: \c"
read app_name
if [ "X${app_name}" = "X" ]; then
    echo "ERROR: Application name cannot be blank. Aborting!"
    exit 2
fi

################# Verify if heroku toolbelt is installed #################
if ! type heroku >/dev/null 2>&1; then
    echo "Installing Heroku CLI toolbelt..."
    sleep 1
    wget -qO- https://toolbelt.heroku.com/install-ubuntu.sh | sh
fi

##################### Compute rediscloud credentials #####################
echo "Creating application ${app_name}..."
if ! heroku create ${app_name} -s cedar --addons rediscloud:25; then
    echo "ERROR: Application create failed. Aborting!"
    exit 1
fi
REDISCLOUD_URL=`heroku config:get REDISCLOUD_URL`
if [ "X${REDISCLOUD_URL}" = "X" ]; then
    echo "ERROR: rediscloud credentials not found. Aborting!"
    exit 2
fi
REDISCLOUD_URL=${REDISCLOUD_URL/redis:\/\/rediscloud:/}
REDIS_PASSWORD=${REDISCLOUD_URL/@*/}
REDISCLOUD_URL=${REDISCLOUD_URL/*@/}
REDIS_HOSTNAME=${REDISCLOUD_URL/:*/}
REDIS_PORT=${REDISCLOUD_URL/*:/}
unset REDISCLOUD_URL

############################## Deploy code ##############################
echo "Deploying code in heroku..."
if git push heroku master; then
    echo "Code successfully deployed in heroku."
else
    echo "ERROR: Operation failed. Aborting!"
    exit 3
fi

######################## Configure application ##########################
echo "...CONFIGURE APPLICATION..."
echo ""
echo -e "Input AWS Access key id: \c"
read AWS_ACCESS_KEY_ID
echo -e "Input AWS secret access key: \c"
read AWS_SECRET_ACCESS_KEY
echo -e "Input SENTRY_DSN for exception tracking by Sentry: \c"
read SENTRY_DSN
echo -e "Input GOOGLE_ID for OAuth 2.0: \c"
read GOOGLE_ID
echo -e "Input GOOGLE_SECRET for OAuth 2.0: \c"
read GOOGLE_SECRET
echo -e "Input AUTHORIZED_EMAILS for login: \c"
read AUTHORIZED_EMAILS


echo "Setting AWS and rediscloud settings..."
heroku config:set AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}"
heroku config:set AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}"
heroku config:set GOOGLE_ID="${GOOGLE_ID}"
heroku config:set GOOGLE_SECRET="${GOOGLE_SECRET}"
heroku config:set AUTHORIZED_EMAILS="${AUTHORIZED_EMAILS}"
if [ "X${SENTRY_DSN}" != "X" ]; then
    heroku config:set SENTRY_DSN="${SENTRY_DSN}"
fi
heroku config:set REDIS_HOST="${REDIS_HOSTNAME}"
heroku config:set REDIS_PORT_NO="${REDIS_PORT}"
heroku config:set REDIS_PASSWORD="${REDIS_PASSWORD}"
heroku config:set PORT="80"
echo ""
echo "Configuration complete."
echo ""

echo "Application url: http://${app_name}.herokuapp.com"
echo "Useful links:"
echo ""
echo "Sync data from AWS: http://${app_name}.herokuapp.com/sync"
echo "Perform lookups: http://${app_name}herokuapp.com/lookup/<search_key>"
echo ""

