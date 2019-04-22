[![Documentation Status](https://readthedocs.org/projects/epcon/badge/?version=latest)](https://readthedocs.org/projects/epcon/?badge=latest)

README
======
This project (and its dependencies) contains the EuroPython website source code.

The code is used for the EuroPython 2019 website.

LICENSE
=======
As a general rule, the whole website code is copyrighted by the Python Italia non-profit association, and released under the 2-clause BSD license (see LICENSE.bsd).

Some CSS files (within directories `p3/static/p4/s` and `p3/static/p5/s`) are instead explicitly marked as non-free; those files implement the current EuroPython website design and Python Italia wants to keep full rights on it. They are still published on GitHub as a reference for implementing a new design.

You are thus welcome to fork away and reuse/enhance this project, as long as you use it to publish a website with a new design (without reusing the current EuroPython design).


INSTALL & SETUP
---------------

Run `provision.sh`. Read it for more details.

Edit `pycon/settings_locale.py` to your taste!

```bash
python manage.py runserver
```

You can access the admin pages using the `admin` username. You can login to the public pages using either `alice@europython.eu` or `bob@europython.eu`. All users' passwords are `europython`.

RUN IN DEBUG MODE
-----------------

```bash
DEBUG=True python manage.py runserver
```

SERVING THE PAGE LOCALLY OVER HTTPS
-----------------

Make sure `sslserver` is in `settings.INSTALLED_APPS`. Then run the server locally using:
```bash
python manage.py runsslserver
```

CONTRIBUTING
------------

1. Make a fork of github.com/europython/epcon
2. Make changes in your fork (ideally on a feature/bugfix branch)
3. Make sure your branch is based on latest upstream/dev/ep2019
    (provision.sh adds europython/epcon as upstream)
4. Push your changes.
5. Create a pull request to europython/epcon, targeting dev/ep2019 branch.

IMPORTANT: all the active development happens on the dev/ep2019 branch, master
is not up to date.


Development Guidelines
----------------------

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
