#!/bin/bash

set -eo pipefail

function title {
    echo -e "\n\n\n" $1 "\n--------"
}

which git   # ensure that git is available before next command
git remote add upstream git@github.com:europython/epcon.git || true

title "Make virtualenv"

virtualenv -p python3.6 ../epcon-env
source ../epcon-env/bin/activate

title "install platform requirements"
if [[ `uname` == "Darwin" ]]; then
    make install-system-dependencies-for-mac
fi
ubuntu_regex='^Distributor ID:[[:space:]]+Ubuntu$'
if [[ -x "$(command -v lsb_release)" && `lsb_release -i` =~ $ubuntu_regex ]]; then
    echo 'Installing missing Ubuntu packages'
    make install-system-dependencies-for-ubuntu
fi

title "PIP install dev requirements"
make install-dev

title "Copy settings"
[[ -e pycon/settings_locale.py ]] || cp pycon/settings_locale.py.in pycon/settings_locale.py

title "Generate data"
make migrate_and_load_initial_data

title "Run tests"
make test
