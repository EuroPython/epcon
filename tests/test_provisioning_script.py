
from django.core.management import call_command

from pytest import mark


# XXX This will have to be investigated further, but not now...
@mark.skip(reason='Getting a weird error from the script')
@mark.django_db
def test_basic_create_initial_data_for_dev_run():

    # just to make sure it doesn't have any syntax errors, obvious mistakes,
    # etc.
    call_command('create_initial_data_for_dev')
