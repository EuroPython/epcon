from django.core.urlresolvers import reverse
from django.test import TestCase
from django_factory_boy import auth as auth_factories

from conference.tests.factories.attendee_profile import AttendeeProfileFactory
from conference.tests.factories.conference import ConferenceFactory


class TestCartView(TestCase):
    def setUp(self):
        self.user = auth_factories.UserFactory(password='password1234', is_superuser=True)
        is_logged = self.client.login(username=self.user.username,
                                      password='password1234')
        AttendeeProfileFactory(user=self.user)
        self.assertTrue(is_logged)

    def test_p3_cart(self):
        url = reverse('p3-cart')

        conference = ConferenceFactory(code='ep2017')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['account_type'], 'p')