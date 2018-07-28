import datetime
import mock

from django.test import TestCase
from django_factory_boy import auth as auth_factories

from conference.tests.factories.attendee_profile import AttendeeProfileFactory
from conference.tests.factories.conference import ConferenceFactory
from conference.tests.factories.fare import TicketFactory, FareFactory
from p3.models import TicketConference
from p3.models import P3Profile
from p3.tests.factories.ticket_conference import TicketConferenceFactory


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

        ticket = TicketFactory(user=self.user)
        ticket_conference = TicketConferenceFactory(ticket=ticket, assigned_to=self.user.email)
        profile =ticket_conference.profile()

        self.assertEqual(attendee_profile, profile)

    def test_assigned_to_email_is_saved_as_lowercase(self):
        """
        The attribute assigned_to of the model TicketConference should
        be always saved in lowercase regardless of input.
        For example: if the input is JoeDoe@Example.com, the field
        assigned_to should be saved as joedoe@example.com

        Issue #740, https://github.com/EuroPython/epcon/issues/740
        EuroPython 2018 Edinburgh, sprints
        author: Cezar Pendarovski
        """
        self.user.email = 'JoeDoe@Example.com'
        self.user.save()
        ticket = TicketFactory(user=self.user)
        ticket_conference = TicketConferenceFactory(ticket=ticket, assigned_to=self.user.email)
        self.assertEqual(self.user.email.lower(), ticket_conference.assigned_to)


class P3ProfileModelTestCase(TestCase):
    def setUp(self):
        self.user = auth_factories.UserFactory()
        self.profile = AttendeeProfileFactory(user=self.user)
        self.p3_profile = P3Profile(profile=self.profile)

    def test_profile_image_url(self):
        from django.conf import settings as dsettings

        url = self.p3_profile.profile_image_url()
        self.assertEqual(url, dsettings.STATIC_URL + dsettings.P3_ANONYMOUS_AVATAR)

        with mock.patch('p3.utils.gravatar') as mock_gravatar:
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

    @mock.patch('conference.models.AttendeeLink.objects.getLink', side_effect=lambda *args, **kwargs: None)
    @mock.patch('conference.models.Conference.objects.current')
    @mock.patch('p3.dataaccess.all_user_tickets')
    @mock.patch('django.core.mail.EmailMessage', return_value=mock.MagicMock())
    def test_send_user_message(self, mock_email_message, mock_user_tickets, mock_current, mock_getLink):
        mock_current.return_value = ConferenceFactory.build(conference_start=datetime.date.today())
        mock_user_tickets.side_effect = lambda a, b: [(1, 'conference', None, True)]

        user_from = auth_factories.UserFactory()
        user_profile = AttendeeProfileFactory(user=user_from)
        self.p3_profile.send_user_message(user_from, 'demo', 'message')

        self.assertTrue(mock_getLink.called)
        self.assertTrue(mock_user_tickets.called)
        self.assertTrue(mock_current.called)
        self.assertTrue(mock_email_message.called)
