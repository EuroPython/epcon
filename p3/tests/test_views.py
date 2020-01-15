from django.core.urlresolvers import reverse
from django.test import TestCase
from django_factory_boy import auth as auth_factories

from tests.factories import AttendeeProfileFactory, ConferenceFactory


class TestView(TestCase):
    def setUp(self):
        self.user = auth_factories.UserFactory(password='password1234', is_superuser=True)
        is_logged = self.client.login(username=self.user.username,
                                      password='password1234')
        AttendeeProfileFactory(user=self.user)
        self.assertTrue(is_logged)

    def test_p3_schedule_empty(self):
        # When trying to view the schedule and no schedule exists, expect 404
        conference = ConferenceFactory()
        url = reverse('schedule:schedule')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
