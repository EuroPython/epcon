#!/bin/bash

function title {
    echo -e "\n\n\n" $1 "\n--------"
}


git remote add upstream git@github.com:europython/epcon.git

title "Make virtualenv"

virtualenv ../pycon-env
source ../pycon-env/bin/activate

title "PIP install dev requirements"
pip install -r requirements-dev.txt


title "Copy settings"
[[ -e pycon/settings_locale.py ]] || cp pycon/settings_locale.py.in pycon/settings_locale.py

title "Create .env file"
[[ -e .env ]] || cp .env.example .env

title "Generate data"
mkdir -p data/site

python manage.py migrate
python manage.py createsuperuser
python manage.py create_initial_data_for_dev


title "Run tests"
py.test
