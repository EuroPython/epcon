# coding: utf-8

from __future__ import unicode_literals, absolute_import

from cms.api import create_page

from django.conf import settings
from django.utils import timezone

from conference.models import Conference


def template_used(response, template_name):
    """
    :response: respone from django test client.
    :template_name: string with path to template.

    :rtype: bool
    """
    return template_name in [t.name for t in response.templates if t.name]


def create_homepage_in_cms():
    # Need to create conference before creating pages
    Conference.objects.get_or_create(code=settings.CONFERENCE_CONFERENCE,
                                     name=settings.CONFERENCE_CONFERENCE)
    create_page(title='HOME', template='django_cms/p5_homepage.html',
                language='en', reverse_id='home', published=True,
                publication_date=timezone.now())
