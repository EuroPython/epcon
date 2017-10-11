[![Documentation Status](https://readthedocs.org/projects/epcon/badge/?version=latest)](https://readthedocs.org/projects/epcon/?badge=latest)

README
======
This project (and its dependencies) contains the EuroPython website source code.

The code is used for the EuroPython 2018 website.

LICENSE
=======
As a general rule, the whole website code is copyrighted by the Python Italia non-profit association, and released under the 2-clause BSD license (see LICENSE.bsd).

Some CSS files (within directories `p3/static/p4/s` and `p3/static/p5/s`) are instead explicitly marked as non-free; those files implement the current EuroPython website design and Python Italia wants to keep full rights on it. They are still published on GitHub as a reference for implementing a new design.

You are thus welcome to fork away and reuse/enhance this project, as long as you use it to publish a website with a new design (without reusing the current EuroPython design).


INSTALL & SETUP
---------------

Run provision.sh. Read it for more details.
Customise your .env file and pycon/settings/locale_dev.py (they are not versioned)

```bash
python manage.py runserver
```

RUN IN DEBUG MODE
-----------------

It's default in dev environment but you can force it using environment
variables

```bash
DEBUG=True python manage.py runserver
```


RUN WITH PRODUCTION SETTINGS
----------------------------

There's a special manage_production.py script that's using a production.py
DJANGO_SETTINGS_MODULE just in case you want to run shell or local server with
production settings (doesn't include secrets, those are provided by env
variables)


CONTRIBUTING
------------

1. Make a fork of github.com/europython/epcon
2. Make changes in your fork (ideally on a feature/bugfix branch)
3. Make sure your branch is based on latest upstream/dev/ep2018
    (provision.sh adds europython/epcon as upstream)
4. Push your changes.
5. Create a pull request to europython/epcon, targeting dev/ep2018 branch.

IMPORTANT: all the active development happens on the dev/ep2018 branch, master
is not up to date.
