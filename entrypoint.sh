#!/bin/sh

if [ "$WAIT_FOR_POSTGRES" = "true" ]
then
    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 3
    done
fi
if [ "$COLLECTSTATIC" = "true" ]
then
    python manage.py collectstatic --noinput
fi
if [ "$MIGRATE" = "true" ]
then
    python manage.py migrate
fi

exec "$@"
