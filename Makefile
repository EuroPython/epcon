
help:
	@echo "\n[UTILS]"
	@echo "dev-requirements - run pip compile and rebuild the dev requirements files"
	@echo "install-dev - install dev dependencies"
	@echo "deployment-requirements - run pip compile and rebuild the production requirements files"
	@echo "install - install production dependencies"
	@echo "install-system-dependencies-for-mac - install mac system dependencies"
	@echo "install-system-dependencies-for-ubuntu - install ubuntu system dependencies"
	@echo "pip-requirements - freeze both dev and production requirements files"
	@echo "pip-tools - install pip and pip-tools"
	@echo "\n[TEST]"
	@echo "test - run all tests"
	@echo "test-no-warnings - run tests without printing warning messages"
	@echo "test-no-django-20-warnings - only disable django 20 deprecation warnings"
	@echo "\n[RUN]"
	@echo "db - create, migrate and load fixtures to the db"
	@echo "drop_db - remove old db"
	@echo "redo_db - drop_db && db"
	@echo "shell - start a django shell"
	@echo "shell-dev - start a django shell (plus)"
	@echo "urls - print url routes"
	@echo "server-dev - start a dev server on port 37266"

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

shell-dev:
	DJANGO_SETTINGS_MODULE="pycon.dev_settings" DEBUG=True ./manage.py shell_plus

shell:
	DEBUG=True ./manage.py shell_plus

urls:
	DJANGO_SETTINGS_MODULE="pycon.dev_settings" DEBUG=True ./manage.py show_urls

-include Makefile.local
