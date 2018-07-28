#!/bin/bash
set -e

if [ "$1" = 'dev' ];
then
    echo "Database migration"
    python manage.py migrate --noinput

    echo "Collect static"
    python manage.py collectstatic --noinput

    echo "Create superuser"
    python manage.py createsuperuser

    echo "Starting website"
    exec python manage.py runserver 0.0.0.0:8000
elif [ "$1" = 'tests' ];
then
    echo "Running tests"
    pip install -r requirements-dev.txt
    py.test -c pytest_ci.ini
else
    echo "Starting website"
    gunicorn pycon.wsgi:application --bind 0.0.0.0:8000 --workers 4
fi
