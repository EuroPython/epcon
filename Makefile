
dev-requirements:
	pip-compile requirements/base.in requirements/dev.in\
		-o requirements/dev.txt

install-dev: pip-tools
	pip-sync requirements/dev.txt

deployment-requirements:
	pip-compile requirements/base.in requirements/deployment.in\
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

test:
	pytest

-include Makefile.local
