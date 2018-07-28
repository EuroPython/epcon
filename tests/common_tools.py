# coding: utf-8

from __future__ import unicode_literals, absolute_import, print_function

import httplib
from wsgiref.simple_server import make_server

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from django_factory_boy import auth as auth_factories

from assopy.tests.factories.user import UserFactory as AssopyUserFactory
from cms.api import create_page
from conference.models import AttendeeProfile
from conference.models import Conference


HTTP_OK = 200


def template_used(response, template_name, http_status=HTTP_OK):
    """
    :response: respone from django test client.
    :template_name: string with path to template.

    :rtype: bool
    """
    assert response.status_code == http_status, response.status_code
    templates = [t.name for t in response.templates if t.name]
    assert template_name in templates, templates
    return True


def template_paths(response):
    """
    This should be used only in project-templates (not 3rd party apps
    templates), to establish which exact template is being rendered (avoidoing
    confusion as to which file is being used)
    """
    paths = []
    for t in response.templates:
        if t.name:
            try:
                path = t.origin.name.split(settings.PROJECT_DIR)[1]
            except IndexError:
                # if there's IndexError that means that template doesn't come
                # from the project (it's probably from a third party app); in
                # that case return full path not relative to the PROJECT_DIR.
                path = t.origin.name

            paths.append(path)

    return paths


def create_homepage_in_cms():
    # Need to create conference before creating pages
    Conference.objects.get_or_create(code=settings.CONFERENCE_CONFERENCE,
                                     name=settings.CONFERENCE_CONFERENCE)
    homepage = create_page(
        title='HOME', template='django_cms/p5_homepage.html', language='en',
        reverse_id='home', published=True, publication_date=timezone.now())
    homepage.set_as_homepage()


def serve_text(text, host='0.0.0.0', port=9876):
    """
    Useful when doing stuff with pdb -- can serve arbitrary string with http.
    use case: looking at some html in tests.

    usage: 1) serve(invoice.html),
           2) go to http://localhost:9876/
           3) PROFIT
    """

    def render(env, start_response):
        status = b'200 OK'
        headers = [(b'Content-Type', b'text/html')]
        start_response(status, headers)
        return [text]

    srv = make_server(host, port, render)
    print("Go to http://{}:{}".format(host, port))
    srv.serve_forever()


def serve_response(response, host='0.0.0.0', port=9876):
    """
    Useful when doing stuff with pdb -- can serve django's response with http.
    use case: looking at response in tests.

    usage: 1) serve(response),
           2) go to http://localhost:9876/
           3) PROFIT
    """

    def render(env, start_response):
        status = b'%s %s' % (
            str(response.status_code),
            httplib.responses[response.status_code]
        )
        # ._headers is a {'content-type': ('Content-Type', 'text/html')} type
        # of dict, that's why we need just .values
        start_response(status, response._headers.values())
        return [response.content]

    srv = make_server(host, port, render)
    print("Go to http://{}:{}".format(host, port))
    srv.serve_forever()


def sequence_equals(sequence1, sequence2):
    """
    Inspired by django's self.assertSequenceEquals

    Useful for comparing lists with querysets and similar situations where
    simple == fails because of different type.
    """
    assert len(sequence1) == len(sequence2), (len(sequence1), len(sequence2))
    for item_from_s1, item_from_s2 in zip(sequence1, sequence2):
        assert item_from_s1 == item_from_s2, (item_from_s1, item_from_s2)

    return True


def make_user(email='joedoe@example.com', **kwargs):
    user = auth_factories.UserFactory(
        email=email, is_active=True,
        **kwargs
    )
    AssopyUserFactory(user=user)
    AttendeeProfile.objects.getOrCreateForUser(user=user)
    return user


def clear_all_the_caches():
    cache.clear()
