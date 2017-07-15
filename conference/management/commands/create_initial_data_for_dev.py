# -*- coding: UTF-8 -*-

from django.core.management.base import BaseCommand
from django.conf import settings

from cms.api import create_page
from conference.models import Conference


class Command(BaseCommand):
    """
    Creates bunch of data that's required for new developer setup.
    Mostly django CMS pages.
    """
    def handle(self, *args, **options):

        Conference.objects.get_or_create(
            code=settings.CONFERENCE_CONFERENCE,
            name=settings.CONFERENCE_CONFERENCE,
        )

        pages = [
            ('home', 'HOME'),
            ('contacts', 'CONTACTS'),
            ('privacy', 'PRIVACY'),
            ('conduct-code', 'CONDUCT-CODE'),
            ('staff', 'STAFF')
        ]

        print "Creating pages: ", pages

        for id, title in pages:
            create_page(title=title, template='django_cms/content.html',
                        language='en', reverse_id=id)
