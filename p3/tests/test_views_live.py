import datetime

from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings

from conference.tests.factories.attendee_profile import AttendeeProfileFactory
from conference.tests.factories.conference import ConferenceFactory

from django_factory_boy import auth as auth_factories

from p3.tests.factories.schedule import ScheduleFactory
from p3.tests.factories.track import TrackFactory


class TestLiveViews(TestCase):
    def setUp(self):
        self.user = auth_factories.UserFactory(password='password1234', is_superuser=True)
        is_logged = self.client.login(username=self.user.username,
                                      password='password1234')
        AttendeeProfileFactory(user=self.user)
        self.assertTrue(is_logged)

    @override_settings(CONFERENCE_CONFERENCE='epbeta', DEBUG=False)
    def test_live_conference(self):
        tmp = ConferenceFactory(code='epbeta', conference_start=datetime.date.today())
        from p3.views.live import _live_conference

        conf, _ = _live_conference()

        self.assertEqual(tmp, conf)

    @override_settings(CONFERENCE_CONFERENCE='epbeta', DEBUG=False)
    def test_live(self):
        ConferenceFactory(code='epbeta', conference_start=datetime.date.today())
        url = reverse('p3-live')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'p3/live.html')
        self.assertEqual(response.context['tracks'].count(), 0)

    @override_settings(CONFERENCE_CONFERENCE='epbeta', DEBUG=False)
    def test_p3_live_track_events(self):
        # p3-live-track-events -> p3.views.live.live_track_events
        conference = ConferenceFactory(code='epbeta', conference_start=datetime.date.today())
        schedule = ScheduleFactory(conference=conference, date=datetime.date.today())
        track = TrackFactory(schedule=schedule)

        # FIXME: track_with_events = TrackWithEventsFactory()

        url = reverse('p3-live-track-events', kwargs={
            'track': track.track,
        })
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('content-type'), 'application/json')
        self.assertJSONEqual(response.content, [])

    @override_settings(CONFERENCE_CONFERENCE='epbeta', DEBUG=False)
    def test_p3_live_events(self):
        # p3-live-events -> p3.views.live.live_events
        url = reverse('p3-live-events')
        conference = ConferenceFactory(code='epbeta', conference_start=datetime.date.today())
        schedule = ScheduleFactory(conference=conference, date=conference.conference_start)
        track = TrackFactory(schedule=schedule)

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('content-type'), 'application/json')
        self.assertJSONEqual(response.content, {})
