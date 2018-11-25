
from django.core.management import call_command

from pytest import mark


@mark.django_db
def test_basic_create_initial_data_for_dev_run():

    # just to make sure it doesn't have any syntax errors, obvious mistakes,
    # etc.
    call_command('create_initial_data_for_dev')
