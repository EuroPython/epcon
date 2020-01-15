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
