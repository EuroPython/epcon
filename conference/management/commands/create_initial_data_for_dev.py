# -*- coding: UTF-8 -*-

from __future__ import print_function

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import FieldError

from cms.api import create_page

from assopy.models import Vat
from conference.fares import pre_create_typical_fares_for_conference
from conference.models import Conference
from tests.common_tools import create_homepage_in_cms

DEFAULT_VAT_RATE = "0.2"  # 20%


class Command(BaseCommand):
    """
    Creates bunch of data that's required for new developer setup.
    Mostly django CMS pages.
    """
    @transaction.atomic
    def handle(self, *args, **options):
        Conference.objects.get_or_create(code=settings.CONFERENCE_CONFERENCE,
                                         name=settings.CONFERENCE_CONFERENCE)

        homepage = create_homepage_in_cms()

        print("Created page: ", homepage.id, homepage.title_set.first().title, homepage.template)

        pages = [
            ('contacts', 'CONTACTS', 'content.html'),
            ('privacy', 'PRIVACY', 'content-1col.html'),
            ('conduct-code', 'CONDUCT-CODE', 'content.html'),
            ('staff', 'STAFF', 'content.html'),
            ('sponsor', 'SPONSOR', 'content.html'),
        ]

        for id, title, template in pages:

            try:
                create_page(
                    title=title,
                    template='django_cms/' + template,
                    language='en',
                    reverse_id=id,
                    published=True,
                    publication_date=timezone.now(),
                )
                print("Created page: ", id, title, template)

            # FieldError happens to be what django cms is using when we want to
            # create another page with the same reverse_id
            except FieldError as e:
                print("Warning: ", e)

        print("Pre creating fares")
        default_vat_rate, _ = Vat.objects.get_or_create(value=DEFAULT_VAT_RATE)
        pre_create_typical_fares_for_conference(
            settings.CONFERENCE_CONFERENCE,
            default_vat_rate,
            print_output=True
        )
