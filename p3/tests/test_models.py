import datetime
from unittest import mock

from django.test import TestCase
from django_factory_boy import auth as auth_factories

from p3.models import TicketConference
from p3.models import P3Profile
from tests.factories import (
    AttendeeProfileFactory,
    ConferenceFactory,
    TicketFactory,
    FareFactory,
    TicketConferenceFactory
)


class TicketConferenceModelTestCase(TestCase):
    def setUp(self):
        self.user = auth_factories.UserFactory()

        self.conference = ConferenceFactory(conference_start=datetime.date.today())
        self.fare = FareFactory(conference=self.conference.code)

    def test_available(self):
        ticket = TicketFactory(user=self.user, fare=self.fare)

        ticket_availables = TicketConference.objects.available(self.user, conference=self.conference)

        self.assertEqual(ticket_availables.count(), 1)

        ticket_availables = TicketConference.objects.available(self.user, conference=None)
        self.assertEqual(ticket_availables.count(), 1)

    def test_profile(self):
        attendee_profile = AttendeeProfileFactory(user=self.user)
        ticket = TicketFactory(user=self.user)
        ticket_conference = TicketConferenceFactory(ticket=ticket)

        profile = ticket_conference.profile()
        self.assertEqual(attendee_profile, profile)

        ticket = TicketFactory(user=self.user, fare=ticket.fare)
        ticket_conference = TicketConferenceFactory(ticket=ticket, assigned_to=self.user.email)
        profile =ticket_conference.profile()

        self.assertEqual(attendee_profile, profile)


class P3ProfileModelTestCase(TestCase):
    def setUp(self):
        self.user = auth_factories.UserFactory()
        self.profile = AttendeeProfileFactory(user=self.user)
        self.p3_profile = P3Profile(profile=self.profile)

    def test_profile_image_url(self):
        from django.conf import settings as dsettings

        url = self.p3_profile.profile_image_url()
        self.assertEqual(url, dsettings.STATIC_URL + dsettings.P3_ANONYMOUS_AVATAR)

        with mock.patch('conference.gravatar.gravatar') as mock_gravatar:
            mock_gravatar.return_value = 'http://www.mockgravatar.com/'
            self.p3_profile.image_gravatar = True
            url = self.p3_profile.profile_image_url()
            self.assertEqual(url, 'http://www.mockgravatar.com/')
            self.p3_profile.image_gravatar = False

        self.p3_profile.image_url = 'http://www.image_url.com'
        url = self.p3_profile.profile_image_url()
        self.assertEqual(url, 'http://www.image_url.com')
        self.p3_profile.image_url = None

        self.p3_profile.profile.image = mock.Mock(url='http://www.image.url.com')
        url = self.p3_profile.profile_image_url()
        self.assertEqual(url, 'http://www.image.url.com')

    def test_public_profile_image_url(self):
        from django.conf import settings as dsettings
        url = self.p3_profile.public_profile_image_url()
        self.assertEqual(url, dsettings.STATIC_URL + dsettings.P3_ANONYMOUS_AVATAR)

        old_visibility = self.p3_profile.profile.visibility
        self.p3_profile.profile.visibility = 'p'
        url = self.p3_profile.public_profile_image_url()
        self.assertEqual(url, dsettings.STATIC_URL + dsettings.P3_ANONYMOUS_AVATAR)
        self.p3_profile.profile.visibility = old_visibility
