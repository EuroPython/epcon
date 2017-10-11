# -*- coding: UTF-8 -*-

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

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
            ('home', 'HOME', 'p5_homepage.html'),
            ('contacts', 'CONTACTS', 'content.html'),
            ('privacy', 'PRIVACY', 'content-1col.html'),
            ('conduct-code', 'CONDUCT-CODE', 'content.html'),
            ('staff', 'STAFF', 'content.html'),
        ]

        for id, title, template in pages:
            print "Creating page: ", id, title, template

            create_page(
                title=title,
                template='django_cms/' + template,
                language='en',
                reverse_id=id,
                published=True,
                publication_date=timezone.now(),
            )
