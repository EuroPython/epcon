import unittest

from django.core.urlresolvers import reverse
from django.test import TestCase

from django_factory_boy import auth as auth_factories

from conference.tests.factories.attendee_profile import AttendeeProfileFactory


class TestView(TestCase):
    def setUp(self):
        self.user = auth_factories.UserFactory(password='password1234', is_superuser=True)
        is_logged = self.client.login(username=self.user.username,
                                      password='password1234')
        AttendeeProfileFactory(user=self.user)
        self.assertTrue(is_logged)


    @unittest.skip("FIXME")
    def test_p3_account_data_get(self):
        # p3-account-data -> p3.views.profile.p3_account_data
        url = reverse('p3-account-data')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


    @unittest.skip("Fix the test with POST method for p3_account_data")
    def test_p3_account_data_post(self):
        # p3-account-data -> p3.views.profile.p3_account_data
        url = reverse('p3-account-data')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

    def test_p3_account_email(self):
        # p3-account-email -> p3.views.profile.p3_account_email
        url = reverse('p3-account-email')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pform']['email'].value(), self.user.email)

    @unittest.skip("FIXME")
    def test_p3_account_spam_control(self):
        # p3-account-spam-control -> p3.views.profile.p3_account_spam_control
        url = reverse('p3-account-spam-control')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


    @unittest.skip("FIXME")
    def test_p3_profile_json(self):
        # p3-profile-json -> p3.views.profile.p3_profile
        url = reverse('p3-profile-json')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


    @unittest.skip("FIXME")
    def test_p3_profile(self):
        # p3-profile -> p3.views.profile.p3_profile
        url = reverse('p3-profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


    @unittest.skip("FIXME")
    def test_p3_profile_avatar(self):
        # p3-profile-avatar -> p3.views.profile.p3_profile_avatar
        url = reverse('p3-profile-avatar')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


    @unittest.skip("FIXME")
    def test_p3_profile_message(self):
        # p3-profile-message -> p3.views.profile.p3_profile_message
        url = reverse('p3-profile-message')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

