# -*- coding: utf-8 -*-

from __future__ import print_function

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import FieldError

from cms.api import create_page, add_plugin
from djangocms_text_ckeditor.cms_plugins import TextPlugin

from assopy import models as assopy_models
from conference.fares import pre_create_typical_fares_for_conference
from conference.models import Conference
from conference.tests.factories.fare import SponsorIncomeFactory
from tests.common_tools import create_homepage_in_cms


DEFAULT_VAT_RATE = "0.2"  # 20%


class Command(BaseCommand):
    """
    Creates bunch of data that's required for new developer setup.
    Mostly django CMS pages.
    """
    @transaction.atomic
    def handle(self, *args, **options):
        conference, _ = Conference.objects.get_or_create(
            code=settings.CONFERENCE_CONFERENCE,
            name=settings.CONFERENCE_CONFERENCE)

        # Create homepage with some sample data.
        homepage = create_homepage_in_cms()
        add_plugin(
            placeholder=homepage.placeholders.get(slot='lead_text'),
            plugin_type=TextPlugin,
            language='en',
            body='This is the lead text')
        add_plugin(
            placeholder=homepage.placeholders.get(slot='home_teaser_text'),
            plugin_type=TextPlugin,
            language='en',
            body='This is the home teaser text')
        # The main_text placeholder does not seem to be used, skipping.

        print("Created page: ", homepage.reverse_id, homepage.title_set.first().title, homepage.template)

        pages = [
            ('contacts', 'CONTACTS', 'content.html'),
            ('privacy', 'PRIVACY', 'content-1col.html'),
            ('conduct-code', 'CONDUCT-CODE', 'content.html'),
            ('staff', 'STAFF', 'content.html'),
            ('sponsor', 'SPONSOR', 'content.html'),
        ]

        for id, title, template in pages:

            try:
                page = create_page(
                    title=title,
                    template='django_cms/' + template,
                    language='en',
                    reverse_id=id,
                    published=True,
                    publication_date=timezone.now(),
                    in_navigation=True,
                )
                print("Created page: ", page.reverse_id, title, page.template)

            # FieldError happens to be what django cms is using when we want to
            # create another page with the same reverse_id
            except FieldError as e:
                print("Warning: ", e)

        print("Creating an admin user")
        assopy_models.User.objects.create_superuser(
            username='admin', email='admin@admin.com', password='europython')

        print("Creating regular users")
        assopy_models.User.objects.create_user(
            email='alice@europython.eu', password='europython', active=True, send_mail=False)
        assopy_models.User.objects.create_user(
            email='bob@europython.eu', password='europython', active=True, send_mail=False)
        assopy_models.User.objects.create_user(
            email='cesar@europython.eu', password='europython', active=True, send_mail=False)

        print("Creating sponsors")
        SponsorIncomeFactory(
            conference=conference,
            sponsor__sponsor='EuroPython Society',
            sponsor__url='https://www.europython-society.org',
            sponsor__logo__color='yellow',
        )
        SponsorIncomeFactory(conference=conference, sponsor__logo__color='blue')
        SponsorIncomeFactory(conference=conference, sponsor__logo__color='orange')
        SponsorIncomeFactory(conference=conference, sponsor__logo__color='teal')
        SponsorIncomeFactory(conference=conference, sponsor__logo__color='purple')
        SponsorIncomeFactory(conference=conference, sponsor__logo__color='red')

        print("Pre creating fares")
        default_vat_rate, _ = assopy_models.Vat.objects.get_or_create(value=DEFAULT_VAT_RATE)
        pre_create_typical_fares_for_conference(
            settings.CONFERENCE_CONFERENCE,
            default_vat_rate,
            print_output=True
        )
