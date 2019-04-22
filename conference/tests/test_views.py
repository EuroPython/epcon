import unittest

from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
from django_factory_boy import auth as auth_factories

from conference.tests.factories.attendee_profile import AttendeeProfileFactory
from conference.tests.factories.conference import ConferenceFactory
from conference.tests.factories.fare import SponsorFactory
from conference.tests.factories.speaker import SpeakerFactory
from conference.tests.factories.talk import TalkFactory
from p3.tests.factories.schedule import ScheduleFactory
from p3.tests.factories.talk import P3TalkFactory


class TestView(TestCase):
    def setUp(self):
        self.user = auth_factories.UserFactory(password='password1234',
                                               is_superuser=True,
                                               is_staff=True)
        is_logged = self.client.login(username=self.user.username,
                                      password='password1234')
        AttendeeProfileFactory(user=self.user)
        self.assertTrue(is_logged)

    @override_settings(DEBUG=False)
    def test_conference_data_xml(self):
        # conference-data-xml -> conference.views.conference_xml
        conference = ConferenceFactory()
        url = reverse('conference-data-xml', kwargs={
            'conference': conference.code,
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('content-type'), 'application/xml')

    @unittest.skip('todo')
    def test_conference_covers(self):
        # conference-covers -> conference.views.covers
        conference = ConferenceFactory()
        url = reverse('conference-covers', kwargs={
            'conference': conference.code,
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    @unittest.skip('todo')
    def test_conference_profile_conferences(self):
        # conference-profile-conferences -> conference.views.user_conferences
        url = reverse('conference-profile-conferences')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    @unittest.skip('todo')
    def test_conference_myself_profile(self):
        # conference-myself-profile -> conference.views.myself_profile
        url = reverse('conference-myself-profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    @unittest.skip('todo')
    def test_conference_profile(self):
        # conference-profile -> conference.views.user_profile
        url = reverse('conference-profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    @unittest.skip('todo')
    def test_conference_paper_submission(self):
        # conference-paper-submission -> conference.views.paper_submission
        url = reverse('conference-paper-submission')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_places(self):
        # conference-places -> conference.views.places
        url = reverse('conference-places')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @override_settings(DEBUG=False)
    def test_conference_schedule_xml(self):
        # conference-schedule-xml -> conference.views.schedule_xml
        conference = ConferenceFactory()
        schedule = ScheduleFactory(conference=conference.code)

        url = reverse('conference-schedule-xml', kwargs={
            'conference': conference.code,
            'slug': schedule.slug,
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('content-type'), 'application/xml')
        self.assertEqual(response.context['schedule'], schedule)

    @unittest.skip('todo')
    def test_conference_schedule(self):
        # conference-schedule -> conference.views.schedule
        url = reverse('conference-schedule')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_schedule_event_booking(self):
        # conference-schedule-event-booking -> conference.views.schedule_event_booking
        url = reverse('conference-schedule-event-booking')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_schedule_event_interest(self):
        # conference-schedule-event-interest -> conference.views.schedule_event_interest
        url = reverse('conference-schedule-event-interest')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_schedule_events_booking_status(self):
        # conference-schedule-events-booking-status -> conference.views.schedule_events_booking_status
        url = reverse('conference-schedule-events-booking-status')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_schedule_events_expected_attendance(self):
        # conference-schedule-events-expected-attendance -> conference.views.schedule_events_expected_attendance
        url = reverse('conference-schedule-events-expected-attendance')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_speaker(self):
        # conference-speaker -> conference.views.speaker
        url = reverse('conference-speaker')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_speaker_xml(self):
        # conference-speaker-xml -> conference.views.speaker_xml
        speaker = SpeakerFactory()

        url = reverse('conference-speaker-xml', kwargs={
            'slug': '123',
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('content-type'), 'application/xml')
        self.assertEqual(response.context['speaker'], speaker)

    @override_settings(DEBUG=False)
    def test_conference_sponsor(self):
        # conference-sponsor-json -> conference.views.sponsor_json
        sponsor = SponsorFactory()
        url = reverse('conference-sponsor-json', kwargs={
            'sponsor': sponsor.slug,
        })

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('content-type'), 'application/json')

        result = {
            'slug': sponsor.slug,
            'sponsor': sponsor.sponsor,
            'url': sponsor.url,
        }

        self.assertJSONEqual(response.content, result)

    def test_conference_talk(self):
        # conference-talk -> conference.views.talk
        conference = ConferenceFactory()
        talk = TalkFactory(conference=conference.code)
        p3_talk = P3TalkFactory(talk=talk)

        url = reverse('conference-talk', kwargs={
            'slug': talk.slug,
        })
        with override_settings(CONFERENCE_CONFERENCE=conference.code):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('content-type'), 'text/html')

    def test_conference_talk_xml(self):
        # conference-talk-xml -> conference.views.talk_xml
        conference = ConferenceFactory()
        talk = TalkFactory(conference=conference.code)
        url = reverse('conference-talk-xml', kwargs={
            'slug': talk.slug,
        })
        with override_settings(CONFERENCE_CONFERENCE=conference.code):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('content-type'), 'application/xml')

    def test_conference_talk_preview(self):
        # conference-talk-preview -> conference.views.talk_preview
        conference = ConferenceFactory()
        talk = TalkFactory(conference=conference.code)
        url = reverse('conference-talk-preview', kwargs={
            'slug': talk.slug,
        })
        with override_settings(CONFERENCE_CONFERENCE=conference.code):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['talk'], talk)

    @unittest.skip('todo')
    def test_conference_talk_video(self):
        # conference-talk-video -> conference.views.talk_video
        url = reverse('conference-talk-video')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_talk_video_mp4(self):
        # conference-talk-video-mp4 -> conference.views.talk_video
        url = reverse('conference-talk-video-mp4')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_profile_link(self):
        # conference-profile-link -> conference.views.user_profile_link
        url = reverse('conference-profile-link')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_profile_link_message(self):
        # conference-profile-link-message -> conference.views.user_profile_link_message
        url = reverse('conference-profile-link-message')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_voting(self):
        # conference-voting -> conference.views.voting
        url = reverse('conference-voting')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
