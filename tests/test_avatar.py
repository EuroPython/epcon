import unittest

from django.urls import reverse
from django.test import TestCase

from . import factories


class TestView(TestCase):
    def setUp(self):
        self.user = factories.UserFactory(password='password1234', is_superuser=True)
        is_logged = self.client.login(username=self.user.username,
                                      password='password1234')
        # self.user_p3_profile = P3ProfileFactory(profile=self.user_profile)
        self.assertTrue(is_logged)

    @unittest.skip("FIXME")
    def test_p3_profile_avatar(self):
        # p3-profile-avatar -> p3.views.profile.p3_profile_avatar
        url = reverse('p3-profile-avatar')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
