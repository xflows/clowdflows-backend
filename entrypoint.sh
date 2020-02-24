#!/bin/sh

pip install -r packages/requirements.txt

if [ "$WAIT_FOR_POSTGRES" = "true" ]
then
    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 3
    done
fi
if [ "$MIGRATE" = "true" ]
then
    python manage.py migrate
    python manage.py import_all
fi
if [ "$COLLECTSTATIC" = "true" ]
then
    python manage.py collectstatic --noinput
fi

exec "$@"
