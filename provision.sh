#!/bin/bash

function title {
    echo -e "\n\n\n" $1 "\n--------"
}


git remote add upstream git@github.com:europython/epcon.git

title "Make virtualenv"

virtualenv -p python2.7 ../pycon-env
source ../pycon-env/bin/activate

title "PIP install dev requirements"
pip install -r requirements-dev.txt

title "Create .env file"
[[ -e .env ]] || cp .env.example .env

title "Create local_dev.py file"
[[ -e pycon/settings/local_dev.py ]] || cp pycon/settings/local_dev.py.in pycon/settings/local_dev.py

title "Generate data"
mkdir -p data/site

python manage.py migrate
python manage.py createsuperuser
python manage.py create_initial_data_for_dev


title "Run tests"
py.test
