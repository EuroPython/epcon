
dev-requirements: pip-tools
	pip-compile --upgrade \
		requirements/base.in\
		requirements/test.in\
		requirements/dev.in\
		-o requirements/dev.txt

install-dev: pip-tools
	pip-sync requirements/dev.txt

deployment-requirements: pip-tools
	pip-compile --upgrade \
		requirements/base.in\
		requirements/test.in\
		requirements/deployment.in\
	   	-o requirements/deployment.txt

install: pip-tools
	pip-sync requirements/deployment.txt

install-system-dependencies-for-mac:
	brew install cairo pango

install-system-dependencies-for-ubuntu:
	sudo apt-get install libxml2-dev libxslt1-dev python-dev

# to make sure both types of requirements are compiled at the same time
pip-requirements: dev-requirements deployment-requirements

pip-tools:
	pip install pip==18.1 --upgrade
	pip install pip-tools

db:
	mkdir -p data/site
	python manage.py migrate
	python manage.py create_initial_data_for_dev
	python manage.py seed_helpdesk


drop_db:
	rm -f data/site/epcon.db

redo_db: drop_db db

test:
	pytest -n auto

test-no-warnings:
	pytest --disable-warnings -n auto

test-no-django-20-warnings:
	pytest -c pytest_no_django_20_warnings.ini

server-dev:
	DJANGO_SETTINGS_MODULE="pycon.dev_settings" DEBUG=True ./manage.py runserver 0:37266

shell:
	DEBUG=True ./manage.py shell_plus

-include Makefile.local
