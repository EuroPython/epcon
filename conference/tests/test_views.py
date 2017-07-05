import unittest

from django.test import TestCase, override_settings
from django.core.urlresolvers import reverse

from conference.tests.factories.conference import ConferenceFactory


class TestView(TestCase):

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
        url = reverse('conference-covers')
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

    @unittest.skip('todo')
    def test_conference_schedule_xml(self):
        # conference-schedule-xml -> conference.views.schedule_xml
        url = reverse('conference-schedule-xml')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

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
    def test_conference_speaker(self):
        # conference-speaker -> conference.views.speaker
        url = reverse('conference-speaker')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_speaker_xml(self):
        # conference-speaker-xml -> conference.views.speaker_xml
        url = reverse('conference-speaker-xml')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_sponsor(self):
        # conference-sponsor -> conference.views.sponsor
        url = reverse('conference-sponsor')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_talk(self):
        # conference-talk -> conference.views.talk
        url = reverse('conference-talk')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_talk(self):
        # conference-talk -> conference.views.talk
        url = reverse('conference-talk')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_talk_xml(self):
        # conference-talk-xml -> conference.views.talk_xml
        url = reverse('conference-talk-xml')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip('todo')
    def test_conference_talk_preview(self):
        # conference-talk-preview -> conference.views.talk_preview
        url = reverse('conference-talk-preview')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

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
    def test_conference_talk_report(self):
        # conference-talk-report -> conference.views.talk_report
        url = reverse('conference-talk-report')
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
    
