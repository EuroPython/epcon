INSTALL
=======

Project dependencies are stored in the file `requirements.txt` and can be
installed using `pip`.

Although not required the use virtualenv is highly recommended.

>>> virtualenv pycon-env

>>> source pycon-env/bin/activate

>>> pip install -r requirements.txt

SETUP
-----

When the install completes you must setup your pycon installation.

>>> cp pycon/settings_locale.py.in pycon/settings_locale.py

Edit `pycon/settings_locale.py` to your taste!

The next step is the database setup; the pycon site uses sqlite so the only
needed thing is to create the directory where the db will be placed.

>>> mkdir -p data/site 

>>> python manage.py syncdb 

>>> python manage.py  

RUN
-----

>>> python manage.py runserver

GETTING STARTED
-----

The first thing you need to do is add 4 pages with the following **ids**:

- HOME (advanced settings->id:home)
- CONTACTS (advanced settings->id:contacts, template: content)
- PRIVACY (advanced settings->id:privacy, template: content page, single column)
- CONDUCT-CODE (advanced settings->id:conduct-code)

If you don't do that you'll start to see some errors like broken url reference. 
NOTE: You may need to restart the server after adding the pages to let the system
detect them.
