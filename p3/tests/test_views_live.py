import datetime
import unittest

import mock
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings, RequestFactory

from conference.tests.factories.attendee_profile import AttendeeProfileFactory
from conference.tests.factories.conference import ConferenceFactory

from django_factory_boy import auth as auth_factories

class TestLiveViews(TestCase):
    def setUp(self):
        self.user = auth_factories.UserFactory(password='password1234', is_superuser=True)
        is_logged = self.client.login(username=self.user.username,
                                      password='password1234')
        AttendeeProfileFactory(user=self.user)
        self.assertTrue(is_logged)

    @override_settings(CONFERENCE='epbeta', DEBUG=False)
    def test_live_conference(self):
        tmp = ConferenceFactory(code='epbeta', conference_start=datetime.date.today())
        from p3.views.live import _live_conference

        conf, _ = _live_conference()

        self.assertEqual(tmp, conf)

    @override_settings(CONFERENCE='epbeta', DEBUG=False)
    def test_live(self):
        ConferenceFactory(code='epbeta', conference_start=datetime.date.today())
        url = reverse('p3-live')
        response = self.client.get(url)

        self.assertEqual(response.templates[0].name, 'p3/live.html')
        self.assertEqual(response.context['tracks'].count(), 0)