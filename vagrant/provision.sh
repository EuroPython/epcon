#!/bin/bash

# Provisioning script for a development Vagrant box.

set -eo pipefail

main() {
    chown vagrant:vagrant /epcon
    apt-get update
    apt-get install -y python-pip python-virtualenv libxslt1-dev libcairo2-dev libpango1.0-dev graphviz

    cat <<DONE

Now ssh into your Vagrant box and run:
    cd /epcon/project
    ./provision.sh
    source /epcon/epcon-env/bin/activate
    python manage.py runserver 0.0.0.0:8000

Outside of the Vagrant box you can browse via:

    http://192.168.50.4:8000/
DONE
}

main