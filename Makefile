
help:
	@echo "[DEV ENV SETUP]"
	@echo "install-docker-ubuntu - installs docker and docker-compose on Ubuntu"
	@echo "install-docker-osx - installs homebrew (you can skip this at runtime), docker and docker-compose on OSX"
	@echo "init-env - builds the container, sets up the database and fixtures"
	@echo "build - builds the container"
	@echo "init-db - sets up the database and fixtures"
	@echo "drop-db - drops the database"
	@echo "redo-db - drops the database, then sets up the database and fixtures"

	@echo "\n[UTILS]"
	@echo "update-requirements - run pip compile and rebuild the requirements files"
	@echo "migrations - generate migrations in a clean container"
	@echo "shell - start a django shell"
	@echo "bash - start a bash shell in a running container"
	@echo "urls - print url routes"

	@echo "\n[TEST]"
	@echo "test - run all tests"
	@echo "test-lf - rerun tests that failed last time"
	@echo "test-no-warnings - run tests without printing warning messages"
	@echo "test-pdb - run tests and enter debugger on failed assert or error"
	@echo "test-n - run all tests using multiple processes"
	@echo "test-n-lf - rerun using multiple processes tests that failed last time"
	@echo "test-n-no-warnings - run tests without printing warning messages"

	@echo "\n[CLEAN]"
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-docker - stop docker containers and remove orphaned images and volumes"
	@echo "clean-py - remove test, coverage and Python file artifacts"

	@echo "\n[PRODUCTION]"
	@echo "deployment-requirements - run pip compile and rebuild the production requirements files"
	@echo "install - install production dependencies"

install-docker-ubuntu:
	sudo apt-get remove docker docker-engine docker.io containerd runc
	sudo apt-get update
	sudo apt-get -y install apt-transport-https ca-certificates curl gnupg-agent software-properties-common
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
	sudo apt-key fingerprint 0EBFCD88
	sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(shell lsb_release -cs) stable"
	sudo apt-get update
	sudo apt-get install -y docker-ce
	sudo curl -L "https://github.com/docker/compose/releases/download/1.23.2/docker-compose-$(shell uname -s)-$(shell uname -m)" -o /usr/local/bin/docker-compose
	sudo chmod +x /usr/local/bin/docker-compose

install-docker-osx:
	/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
	brew update
	brew cask install docker
	brew install docker-compose

init-env: build init-db

build:
	docker-compose build --pull epcon

run:
	docker-compose up

init-db:
	docker-compose down -t 60
	mkdir -p data/site
	docker-compose run --rm epcon "./manage.py migrate --no-input"
	docker-compose run --rm epcon "./manage.py create_initial_data_for_dev"

drop-db:
	docker-compose down -t 60
	rm -f data/site/epcon.db

redo-db: drop-db init-db

update-requirements: build
	docker-compose run --rm epcon "pip install pip-tools -U && pip-compile -U --generate-hashes requirements.in -o requirements.txt && chmod a+r requirements.txt && pip-compile -U requirements-dev.in -o requirements-dev.txt && chmod a+r requirements-dev.txt"

migrations: build
	docker-compose run --rm epcon "./manage.py makemigrations"

shell:
	docker-compose run --rm epcon "./manage.py shell_plus"

bash:
	docker-compose exec epcon /bin/bash

urls:
	docker-compose run --rm epcon "./manage.py show_urls"

test: build
	docker-compose run --rm epcon "pytest"

test-pdb:
	docker-compose run --rm epcon "pytest --pdb"

test-lf:
	docker-compose run --rm epcon "pytest --lf"

test-no-warnings:
	docker-compose run --rm epcon "pytest --disable-warnings"

test-n:
	docker-compose run --rm epcon "pytest -n auto"

test-n-lf:
	docker-compose run --rm epcon "pytest -n auto -lf"

test-n-no-warnings:
	docker-compose run --rm epcon "pytest --disable-warnings -n auto"

clean: clean-docker clean-py

clean-docker:
	docker-compose down -t 60
	docker system prune -f

clean-py:
	find . -name '*.pyc' -delete
	find . -name '*.pyo' -delete
	find . -name '.coverage' -delete

deployment-requirements:
	pip install -U pip==19.3.1
	pip install -U pip-tools
	pip-compile --upgrade requirements.in -o requirements.txt
	chmod a+r requirements.txt

install:
	pip install -U pip
	pip install -U pip-tools
	pip-sync requirements.txt

-include Makefile.local
