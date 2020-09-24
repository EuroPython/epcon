#!/bin/bash -eux

if [ $# -eq 0 ]; then
    echo "No database provided"
    exit 1
fi

# Check sqlite3 is installed
sqlite3 --version

# Delete invalid test accounts and create a dump for data incompatible with Django2 migrations
cat ./scripts/django2_migration.sql | sqlite3 $1

# Migrate the latest Django2 DB changes
./manage.py migrate

# Import previously dumped data after the migration
sed -i '1i BEGIN TRANSACTION;' /tmp/assopy_invoice.sql
echo 'END TRANSACTION;' >> /tmp/assopy_invoice.sql
cat /tmp/assopy_invoice.sql | sqlite3 $1

sed -i '1i BEGIN TRANSACTION;' /tmp/conference_vototalk.sql
echo 'END TRANSACTION;' >> /tmp/conference_vototalk.sql
cat /tmp/conference_vototalk.sql | sqlite3 $1

sed -i '1i BEGIN TRANSACTION;' /tmp/conference_event.sql
echo 'END TRANSACTION;' >> /tmp/conference_event.sql
cat /tmp/conference_event.sql | sqlite3 $1
