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

Run provision.sh. Read it for more details.

Edit `pycon/settings_locale.py` to your taste!

```bash
python manage.py runserver
```

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
