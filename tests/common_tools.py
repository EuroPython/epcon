# coding: utf-8

from __future__ import unicode_literals, absolute_import

from wsgiref.simple_server import make_server

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
    templates = [t.name for t in response.templates if t.name]
    assert template_name in templates, templates
    return True


def create_homepage_in_cms():
    # Need to create conference before creating pages
    Conference.objects.get_or_create(code=settings.CONFERENCE_CONFERENCE,
                                     name=settings.CONFERENCE_CONFERENCE)
    create_page(title='HOME', template='django_cms/p5_homepage.html',
                language='en', reverse_id='home', published=True,
                publication_date=timezone.now())


def serve(content, host='0.0.0.0', port=9876):
    """
    Useful when doing stuff with pdb -- can serve aribtrary string with http.

    use case: looking at response.content in tests.

    usage: 1) serve(response.content),
           2) go to http://localhost:9876/
           3) PROFIT
    """

    def render(env, sr):
        sr(b'200 OK', [(b'Content-Type', b'text/html'), ])
        return [content]

    srv = make_server(host, port, render)
    print "Go to http://{}:{}".format(host, port)
    srv.serve_forever()
