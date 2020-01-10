import unittest

from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings
from django_factory_boy import auth as auth_factories

from tests.factories import (
    AttendeeProfileFactory, ConferenceFactory, SponsorFactory,
    SpeakerFactory, TalkFactory, ScheduleFactory,
)


class TestView(TestCase):
    def setUp(self):
        self.user = auth_factories.UserFactory(password='password1234',
                                               is_superuser=True,
                                               is_staff=True)
        is_logged = self.client.login(username=self.user.username,
                                      password='password1234')
        AttendeeProfileFactory(user=self.user)
        self.assertTrue(is_logged)

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
    def test_conference_speaker(self):
        # conference-speaker -> conference.views.speaker
        url = reverse('conference-speaker')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

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
        """
        Test the view redirects to the new talk detail view.
        """
        # conference-talk -> conference.views.talk
        conference = ConferenceFactory()
        talk = TalkFactory(conference=conference.code)

        url = reverse('conference-talk', kwargs={
            'slug': talk.slug,
        })

        response = self.client.get(url)

        self.assertRedirects(
            response, reverse('talks:talk', kwargs={'talk_slug': talk.slug}), status_code=301
        )

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
