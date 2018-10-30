
dev-requirements: pip-tools
	pip-compile\
		requirements/base.in\
		requirements/test.in\
		requirements/dev.in\
		-o requirements/dev.txt

install-dev: pip-tools
	pip-sync requirements/dev.txt

deployment-requirements: pip-tools
	pip-compile \
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
	pip install pip-tools

migrate_and_load_initial_data:
	mkdir -p data/site
	python manage.py migrate
	python manage.py create_initial_data_for_dev

test:
	pytest

-include Makefile.local
