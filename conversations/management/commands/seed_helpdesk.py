
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction

from faker import Faker

from conference.models import Conference
from conversations.models import Thread, Attachment
from conversations.helpdesk import (
    create_new_support_request,
    staff_reply_to_thread,
)


CONFIRMED_DROP = 'y'

fake = Faker()


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

        print(
            Thread.objects.filter(category=Thread.CATEGORIES.HELPDESK).delete()
        )

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
            title=fake.sentence(nb_words=6, variable_nb_words=True),
            content=fake.sentence(nb_words=6, variable_nb_words=True),
            attachments=[attachment1]
        )
