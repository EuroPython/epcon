import unittest

import factory
import mock
import simplejson
from django.core.urlresolvers import reverse
from django.test import TestCase
from django_factory_boy import auth as auth_factories

from conference.tests.factories.attendee_profile import AttendeeProfileFactory
from p3.tests.factories.profile import P3ProfileFactory


class MessageFactory(object):
    subject = factory.Faker('sentence', nb_words=6, variable_nb_words=True, ext_word_list=None)
    message = factory.Faker('paragraph', nb_sentences=3, variable_nb_sentences=True, ext_word_list=None)


class TestView(TestCase):
    def setUp(self):
        self.user = auth_factories.UserFactory(password='password1234', is_superuser=True)
        is_logged = self.client.login(username=self.user.username,
                                      password='password1234')
        self.user_profile = AttendeeProfileFactory(user=self.user)
        self.user_p3_profile = P3ProfileFactory(profile=self.user_profile)
        self.assertTrue(is_logged)

    def test_p3_account_data_error(self):
        # p3-account-data -> p3.views.profile.p3_account_data
        url = reverse('p3-account-data')
        self.client.logout()
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)

    def test_p3_account_data_get(self):
        # p3-account-data -> p3.views.profile.p3_account_data
        url = reverse('p3-account-data')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'assopy/profile_personal_data.html')

    def test_p3_account_data_post(self):
        # p3-account-data -> p3.views.profile.p3_account_data
        first_name, last_name = self.user.first_name, self.user.last_name
        url = reverse('p3-account-data')
        response = self.client.post(url, data={
            'first_name': self.user.last_name,
            'last_name': self.user.first_name,
        })
        self.assertEqual(response.status_code, 200)

        from django.contrib.auth.models import User
        user = User.objects.get(pk=self.user.id)
        self.assertEqual(user.first_name, last_name)
        self.assertEqual(user.last_name, first_name)

    def test_p3_account_email(self):
        # p3-account-email -> p3.views.profile.p3_account_email
        url = reverse('p3-account-email')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pform']['email'].value(), self.user.email)

    def test_p3_profile_json(self):
        # p3-profile-json -> p3.views.profile.p3_profile
        url = reverse('p3-profile-json', kwargs={
            'slug': self.user_profile.slug,
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json_content = simplejson.loads(response.content)
        dict_content = {
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'slug': self.user_profile.slug,
        }
        self.assertDictContainsSubset(dict_content, json_content)

    def test_p3_profile(self):
        # p3-profile -> p3.views.profile.p3_profile
        url = reverse('p3-profile', kwargs={
            'slug': self.user_profile.slug,
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @unittest.skip("FIXME")
    def test_p3_profile_avatar(self):
        # p3-profile-avatar -> p3.views.profile.p3_profile_avatar
        url = reverse('p3-profile-avatar')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_p3_profile_message_refuse_message(self):

        # p3-profile-message -> p3.views.profile.p3_profile_message
        url = reverse('p3-profile-message', kwargs={
            'slug': self.user_profile.slug,
        })
        message = MessageFactory()
        response = self.client.post(url, data={
            'subject': message.subject,
            'message': message.message,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, 'This user does not want to receive a message')

    def test_p3_profile_message_accept_message(self):
        # p3-profile-message -> p3.views.profile.p3_profile_message
        user = auth_factories.UserFactory()
        user_profile = AttendeeProfileFactory(user=user)
        user_p3_profile = P3ProfileFactory(profile=user_profile)

        url = reverse('p3-profile-message', kwargs={
            'slug': user_profile.slug,
        })

        with mock.patch('p3.models.P3Profile.send_user_message'):
            # We need to simulate the send_user_message method because there is a lot of checks
            # in the code.
            message = MessageFactory()

            response = self.client.post(url, data={
                'subject': message.subject,
                'message': message.message,
            })

            self.assertEqual(response.status_code, 200)
            self.assertEqual(simplejson.loads(response.content), 'OK')
