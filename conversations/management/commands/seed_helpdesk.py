import random

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django import forms

from faker import Faker

from conference.models import Conference
from conversations.models import Thread, Attachment
from conversations.helpdesk.api import create_new_support_request
from conversations.finaid.api import create_new_finaid_request
from conversations.common_actions import staff_reply_to_thread
from conversations.user_interface import UserNewFinaidRequest


CONFIRMED_DROP = 'y'

fake = Faker()


def fake_data_based_on_django_form(django_form):
    output = {}

    for k, v in django_form.declared_fields.items():

        if isinstance(v, forms.CharField):
            output[k] = fake.pystr()

        elif isinstance(v, forms.IntegerField):
            output[k] = fake.pyint()

        elif isinstance(v, forms.MultipleChoiceField):
            num_of_items = random.randrange(len(v.choices))
            output[k] = random.sample(
                [x[0] for x in v.choices],
                num_of_items,
            )

        elif isinstance(v, forms.ChoiceField):
            output[k] = random.choice([x[0] for x in v.choices])

        elif isinstance(v, forms.DateField):
            output[k] = fake.date_object()

        else:
            raise NotImplementedError("not supported", (k, v))

    # TODO: support for attachments/files
    return output


class Command(BaseCommand):
    """
    Creates bunch of data that's required to test helpdesk
    """

    @transaction.atomic
    def handle(self, *args, **options):
        conference = Conference.objects.current()

        print('This will drop all the heldpesk data in the database')
        confirm = input('Do you want to proceed? [y/N] ')

        if confirm != CONFIRMED_DROP:
            return 'Nope, not dropping anything'

        print(Thread.objects.all().delete())

        # Need two users and two admins
        users = User.objects.filter(is_staff=False).order_by("?")[:2]
        assert len(users) == 2, "Need at least two regular users"

        admins = User.objects.filter(is_staff=True).order_by("?")[:2]
        assert len(admins) == 2, "Need at least two admins"

        # Create new things
        create_new_support_request(
            conference,
            users[0],
            title=fake.sentence(nb_words=6, variable_nb_words=True),
            content=fake.sentence(nb_words=6, variable_nb_words=True),
        )

        # Replied request
        thread, _  = create_new_support_request(
            conference,
            users[0],
            title=fake.sentence(nb_words=6, variable_nb_words=True),
            content=fake.sentence(nb_words=6, variable_nb_words=True),
        )

        staff_reply_to_thread(
            thread,
            admins[0],
            content=fake.sentence(nb_words=6, variable_nb_words=True),
        )

        # Something with attachment, also actionable
        attachment1 = Attachment.objects.create(
            message=None,
            file=SimpleUploadedFile('info.txt', b'Some additional content')
        )

        thread, _  = create_new_support_request(
            conference,
            users[0],
            title='Attached! ' + fake.sentence(
                nb_words=6, variable_nb_words=True
            ),
            content=fake.sentence(nb_words=6, variable_nb_words=True),
            attachments=[attachment1]
        )

        # Finaid
        thread, _ = create_new_finaid_request(
            conference,
            users[0],
            finaid_data=fake_data_based_on_django_form(UserNewFinaidRequest)
        )

        thread, _ = create_new_finaid_request(
            conference,
            users[1],
            finaid_data=fake_data_based_on_django_form(UserNewFinaidRequest)
        )
