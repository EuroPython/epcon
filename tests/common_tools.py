import http.client
from datetime import date
from urllib.parse import urlparse

from wsgiref.simple_server import make_server

from django.conf import settings
from django.core.cache import cache

from django_factory_boy import auth as auth_factories

from assopy.models import Vat, VatFare
from conference.accounts import get_or_create_attendee_profile_for_new_user
from conference.models import AttendeeProfile, TALK_STATUS, Fare
from conference.fares import pre_create_typical_fares_for_conference
from tests.factories import (
    AssopyUserFactory, OrderFactory, TalkFactory, SpeakerFactory, TalkSpeakerFactory, ConferenceFactory,
)

HTTP_OK = 200
DEFAULT_VAT_RATE = "7.7"  # 7.7%


def template_used(response, template_name, http_status=HTTP_OK):
    """
    :response: respone from django test client.
    :template_name: string with path to template.

    :rtype: bool
    """
    assert response.status_code == http_status, response.status_code
    templates = [t.name for t in response.templates if t.name]
    if templates:
        assert template_name in templates, templates
    else:
        assert response.template_name == template_name, response.template_name
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
            http.client.responses[response.status_code]
        )
        # ._headers is a {'content-type': ('Content-Type', 'text/html')} type
        # of dict, that's why we need just .values
        start_response(status, list(response._headers.values()))
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


def redirects_to(response, url):
    """
    Inspired by django's self.assertRedirects

    Useful for confirming the response redirects to the specified url.
    """
    is_redirect = response.status_code == 302
    parsed_url = urlparse(response.get('Location'))
    is_url = parsed_url.path == url

    return is_redirect and is_url


def contains_message(response, message):
    """
    Inspired by django's self.assertRaisesMessage

    Useful for confirming the response contains the provided message,
    """
    if len(response.context['messages']) != 1:
        return False

    full_message = str(list(response.context['messages'])[0])

    return message in full_message


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


def is_using_jinja2_template(response):
    res = response.resolve_template(response.template_name)
    assert res.backend.name == "jinja2", res.backed.name
    return True


def setup_conference_with_typical_fares(start=date(2019, 7, 8), end=date(2019, 7, 14)):
    conference = get_default_conference(
        conference_start=start,
        conference_end=end,
    )
    default_vat_rate, _ = Vat.objects.get_or_create(value=DEFAULT_VAT_RATE)
    fares = pre_create_typical_fares_for_conference(
        settings.CONFERENCE_CONFERENCE,
        default_vat_rate
    )

    return conference, fares


def create_valid_ticket_for_user_and_fare(user, fare=None):
    setup_conference_with_typical_fares()
    default_vat_rate, _ = Vat.objects.get_or_create(value=DEFAULT_VAT_RATE)

    if not fare:
        fare = Fare.objects.first()
    VatFare.objects.get_or_create(vat=default_vat_rate, fare=fare)

    order = OrderFactory(
        user=user.assopy_user,
        items=[(fare, {"qty": 1}),],
    )
    order._complete=True
    order.save()

    ticket = order.orderitem_set.first().ticket
    assert ticket.user == user
    return ticket


def get_default_conference(**kwargs):
    return ConferenceFactory(**kwargs)


def create_talk_for_user(user, **kwargs):
    if user is None:
        user = create_user()

    talk = TalkFactory(**{'status': TALK_STATUS.proposed, 'created_by': user, **kwargs})
    speaker = SpeakerFactory(user=user)
    TalkSpeakerFactory(talk=talk, speaker=speaker)
    return talk


def create_user():
    user = auth_factories.UserFactory(is_active=True)
    AssopyUserFactory(user=user)
    get_or_create_attendee_profile_for_new_user(user)
    return user
