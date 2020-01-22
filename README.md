[![Travis-CI Status](https://travis-ci.org/EuroPython/epcon.svg?branch=default)](https://travis-ci.org/EuroPython/epcon)
[![Documentation Status](https://readthedocs.org/projects/epcon/badge/?version=latest)](https://readthedocs.org/projects/epcon/?badge=latest)

# README

This project (and its dependencies) contains the EuroPython website source code.

The code is used for the EuroPython 2020 website.

# LICENSE

As a general rule, the whole website code is copyrighted by the Python Italia non-profit association, and released under the 2-clause BSD license (see LICENSE.bsd).

Some CSS files (within directories `p3/static/p4/s` and `p3/static/p5/s`) are instead explicitly marked as non-free; those files implement the current EuroPython website design and Python Italia wants to keep full rights on it. They are still published on GitHub as a reference for implementing a new design.

You are thus welcome to fork away and reuse/enhance this project, as long as you use it to publish a website with a new design (without reusing the current EuroPython design).


# DEVELOPMENT

## Pre-requisites

In order to run the project locally, you need to have [Docker](https://docs.docker.com/install/)
and [docker-compose](https://docs.docker.com/compose/overview/) installed.

You can install the above mentioned packages manually or you can use our helper commands.

On `Ubuntu 18.04+` run:
```bash
$ make install-docker-ubuntu
```

On `MacOS` run:
```bash
$ make install-docker-osx
```

On other platforms please follow the instructions described here:
- https://docs.docker.com/install/
- https://docs.docker.com/compose/install/

The minimum versions the Makefile was tested with are:

```bash
$ docker --version
Docker version 18.09.2, build 6247962
$ docker-compose --version
docker-compose version 1.23.2, build 1110ad01
```

# Development env setup

Initialise the database and development fixtures:

```bash
$ make init-env
```

Get the project up and running:

```bash
$ docker-compose up
```

You can access the admin pages using the `admin` username. You can login to the public pages using either `alice@europython.eu` or `bob@europython.eu`. All users' passwords are `europython`.

## Debugging with VS Code

To start a server with the VS Code debugger enabled, run:

```bash
$ docker -f docker-compose.yml -f docker-compose-vscode-debugger.yml up
```

Next, run "Start Debugging" command in VS Code (otherwise, the `docker-compose up`
command will be *stuck* waiting for the debugger to attach).
Now you can put breakpoints in your code (even in the Django template files).

## Testing

```bash
$ make test
```

# CONTRIBUTING

1. Make a fork of github.com/europython/epcon
2. Make changes in your fork (ideally on a feature/bugfix branch)
3. Make sure your branch is based on latest `upstream/dev/ep2020`
4. Push your changes
5. Create a pull request to `europython/epcon`, targeting `dev/ep2020` branch.

IMPORTANT: all the active development happens on the `dev/ep2020` branch, `master` is not up to date.


## Development Guidelines

To give you some direction of where we're going with the codebase, here's a
short of list of things we have in mind for the near future.

* The current codebase needs major refactorings and updates, and we really
  appreciate all the help, but before doing anything big please talk to us
  (EuroPython Web WG), so we can coordinate with other ongoing developments.

  You can use github issues for that, or find us on our public telegram group
  here -> https://t.me/sprintseuropythonsite

* We currently have three major django apps – p3, assopy and conference. They
  are here for historical reasons, and our plan forward is to slowly get rid of
  p3 and assopy and replace all of them with just conference app. (This is very
  long term plan)

* We've chosen to go with an approach of rewriting the epcon 'in place', which
  in plain English means we're adding new features and APIs (python functions
  and classes) within `conference/` app, and then slowly removing old pieces of
  logic from old apps. See `conference/invoicing.py` for an example.

* We use pytest and prefer the pytest tests over DjangoTestCase tests, however
  both are fine. Similar as above, we have a new `tests/` directory and we put
  all tests, organised by topic, in those files. See `tests/test_invoicing.py`

* We prefer integration tests (ie. using django test client) over unit tests,
  particulary for old features/pieces of code. Given that our current test
  coverage is lower than we'd like it to be, pull requests that just add tests
  are very welcome.

* We also like WIP (Work In Progress) pull requests, and Proof-of-Concept
  proposals. If you'd like to work on something, that may take a long time,
  please open WIP PR (and add WIP to the title)

* Branch names that start with `feature/` `bugfix/` `tests/` and have
  descriptive names like `docs/update-readme-with-dev-guidelines` are
  preferable to 'patch-1' ;)
