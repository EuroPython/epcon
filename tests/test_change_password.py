# coding: utf-8

from __future__ import unicode_literals, absolute_import

from pytest import mark

from django.core.urlresolvers import reverse

from django_factory_boy import auth as auth_factories

# TODO: clean up this import path
from assopy.tests.factories.user import UserFactory as AssopyUserFactory
from conference.models import AttendeeProfile

from tests.common_tools import template_used


@mark.django_db
def test_change_password(client):
    """
    Testing full change password flow,

    1. Log in
    2. Look for change password url on the profile page
    3. Change the password.
    4. Log in with new password
    """

    # default password is 'password123' per django_factory_boy
    user = auth_factories.UserFactory(email='joedoe@example.com',
                                      is_active=True)

    # both are required to access user profile page.
    AssopyUserFactory(user=user)
    AttendeeProfile.objects.create(user=user, slug='foobar')

    client.login(email='joedoe@example.com', password='password123')

    user_profile_url = reverse("assopy-profile")
    change_password_url = reverse("password_change")

    response = client.get(user_profile_url)
    assert "Change your password" in response.content.decode('utf-8')
    assert change_password_url in response.content.decode('utf-8')
    assert template_used(response, 'assopy/profile.html')

    response = client.get(change_password_url)
    assert template_used(response, "registration/password_change_form.html")
    assert 'Django Administration' not in response.content

    response = client.post(change_password_url, {
        'old_password': 'password123',
        'new_password1': 'pwd345',
        'new_password2': 'pwd345',
    }, follow=True)

    assert template_used(response, "registration/password_change_done.html")
    assert user_profile_url in response.content
    assert 'Password change successful' in response.content
    assert 'Go back to your profile' in response.content

    client.logout()

    can_log_in_with_new_password = client.login(email='joedoe@example.com',
                                                password='pwd345')
    assert can_log_in_with_new_password
