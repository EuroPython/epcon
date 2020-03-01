#!/bin/bash -eux

if [ $# -eq 0 ]; then
    echo "No database provided"
    exit 1
fi

cat ./scripts/django2_migration.sql | sqlite3 $1

./manage.py migrate

cat /tmp/assopy_invoice.sql | sqlite3 $1
cat /tmp/conference_vototalk.sql | sqlite3 $1
cat /tmp/conference_event.sql | sqlite3 $1
