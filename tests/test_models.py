import datetime
from unittest import mock

from django.conf import settings

import pytest

from p3.models import TicketConference
from p3.models import P3Profile
from tests.factories import (
    AttendeeProfileFactory,
    ConferenceFactory,
    TicketFactory,
    FareFactory,
    TicketConferenceFactory
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def p3_profile(user):
    profile = AttendeeProfileFactory(user=user)
    return P3Profile(profile=profile)


def test_available_tickets(user):
    conference = ConferenceFactory(conference_start=datetime.date.today())
    fare = FareFactory(conference=conference.code)

    TicketFactory(user=user, fare=fare)
    ticket_availables = TicketConference.objects.available(user, conference=conference)
    assert ticket_availables.count() == 1

    ticket_availables = TicketConference.objects.available(user, conference=None)
    assert ticket_availables.count() == 1


def test_atendee_profile(user):
    attendee_profile = AttendeeProfileFactory(user=user)
    ticket = TicketFactory(user=user)
    ticket_conference = TicketConferenceFactory(ticket=ticket)

    profile = ticket_conference.profile()
    assert attendee_profile == profile

    ticket = TicketFactory(user=user, fare=ticket.fare)
    ticket_conference = TicketConferenceFactory(ticket=ticket, assigned_to=user.email)
    profile = ticket_conference.profile()

    assert attendee_profile == profile


@pytest.mark.parametrize(
    "email_input,email_expected",
    [
        ("User.Test@example.test", "user.test@example.test"),
        ("  User.Test@example.test    ", "user.test@example.test"),
        ("USER-TEST3@EXAMPLE.test", "user-test3@example.test"),
    ]
)
def test_email_is_lowercased_and_stripped(email_input, email_expected, user):
    ticket = TicketFactory(user=user)
    ticket_conference = TicketConferenceFactory(ticket=ticket, assigned_to=email_input)
    assert ticket_conference.assigned_to == email_expected


def test_profile_image_url(p3_profile):
    url = p3_profile.profile_image_url()
    assert url == settings.STATIC_URL + settings.P3_ANONYMOUS_AVATAR

    with mock.patch('conference.gravatar.gravatar') as mock_gravatar:
        mock_gravatar.return_value = 'http://www.mockgravatar.test/'
        p3_profile.image_gravatar = True
        url = p3_profile.profile_image_url()
        assert url == 'http://www.mockgravatar.test/'
        p3_profile.image_gravatar = False

    p3_profile.image_url = 'http://www.image_url.test'
    url = p3_profile.profile_image_url()
    assert url == 'http://www.image_url.test'
    p3_profile.image_url = None

    p3_profile.profile.image = mock.Mock(url='http://www.image.url.test')
    url = p3_profile.profile_image_url()
    assert url == 'http://www.image.url.test'


def test_public_profile_image_url(p3_profile):
    url = p3_profile.public_profile_image_url()
    assert url == settings.STATIC_URL + settings.P3_ANONYMOUS_AVATAR

    p3_profile.profile.visibility = 'p'
    url = p3_profile.public_profile_image_url()
    assert url == settings.STATIC_URL + settings.P3_ANONYMOUS_AVATAR
