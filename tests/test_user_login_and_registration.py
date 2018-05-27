# coding: utf-8

from __future__ import unicode_literals, absolute_import

from pytest import mark

from django.core.urlresolvers import reverse

from email_template.models import Email

from assopy.models import User
from assopy.forms import (
    PRIVACY_POLICY_CHECKBOX,
    PRIVACY_POLICY_ERROR
)

from tests.common_tools import (
    create_homepage_in_cms,
    template_used
)


SIGNUP_SUCCESFUL_303 = 303
SIGNUP_FAILED_200    = 200


@mark.django_db
def test_user_registration(client):
    """
    Tests if users can create new account on the website
    (to buy tickets, etc).
    """
    # required for redirects to /
    create_homepage_in_cms()

    # 1. test if user can create new account
    sign_up_url = "/accounts/new-account/"
    response = client.get(sign_up_url)
    assert response.status_code == 200

    assert template_used(response, "assopy/new_account.html")
    assert template_used(response,
                         "registration/partials/_login_with_google.html")
    assert template_used(response, 'assopy/new_account.html')
    assert template_used(response, "assopy/base.html")
    assert template_used(response, "p3/base.html")
    assert PRIVACY_POLICY_CHECKBOX in response.content

    assert User.objects.all().count() == 0

    # need to create an email template that's used in the signup process
    Email.objects.create(code='verify-account')

    response = client.post(sign_up_url, {
        'first_name': 'Joe',
        'last_name': 'Doe',
        'email': 'joedoe@example.com',
        'password1': 'password',
        'password2': 'password',
    }, follow=True)

    assert response.status_code == SIGNUP_FAILED_200
    assert "/privacy/"                        in PRIVACY_POLICY_CHECKBOX
    assert "I consent to the use of my data"  in PRIVACY_POLICY_CHECKBOX
    assert response.context['form'].errors['__all__'] == [PRIVACY_POLICY_ERROR]

    response = client.post(sign_up_url, {
        'first_name': 'Joe',
        'last_name': 'Doe',
        'email': 'joedoe@example.com',
        'password1': 'password',
        'password2': 'password',
        'i_accept_privacy_policy': True,
    }, follow=True)

    # check if redirect was correct
    assert template_used(response, 'assopy/new_account_feedback.html')
    assert template_used(response, "assopy/base.html")
    assert template_used(response, "p3/base.html")

    user = User.objects.get()
    assert user.name() == "Joe Doe"

    assert not user.user.is_active

    is_logged_in = client.login(email="joedoe@example.com",
                                password='password')
    assert not is_logged_in  # user is inactive

    response = client.get('/', follow=True)  # will redirect to /en/
    assert template_used(response, 'django_cms/p5_homepage.html')
    assert 'Joe Doe' not in response.content
    assert 'Log out' not in response.content

    # enable the user
    user.user.is_active = True
    user.user.save()

    is_logged_in = client.login(email="joedoe@example.com",
                                password='password')
    assert is_logged_in

    response = client.get('/', follow=True)  # will redirect to /en/
    assert template_used(response, 'django_cms/p5_homepage.html')
    # checking if user is logged in.
    assert 'Joe Doe' in response.content
    assert 'Log out' in response.content


@mark.django_db
def test_393_emails_are_lowercased_and_login_is_case_insensitive(client):
    """
    https://github.com/EuroPython/epcon/issues/393

    Test if we can regiester new account if we use the same email with
    different case.
    """

    create_homepage_in_cms()
    Email.objects.create(code='verify-account')

    sign_up_url = "/accounts/new-account/"

    response = client.post(sign_up_url, {
        'first_name': 'Joe',
        'last_name': 'Doe',
        'email': 'JoeDoe@example.com',
        'password1': 'password',
        'password2': 'password',
        'i_accept_privacy_policy': True,
    })
    assert response.status_code == SIGNUP_SUCCESFUL_303

    user = User.objects.get()
    assert user.name() == "Joe Doe"
    assert user.user.email == 'joedoe@example.com'

    response = client.post(sign_up_url, {
        'first_name': 'Joe',
        'last_name': 'Doe',
        'email': 'jOEdOE@example.com',
        'password1': 'password',
        'password2': 'password',
        'i_accept_privacy_policy': True,
    })
    assert response.status_code == SIGNUP_FAILED_200
    assert response.context['form'].errors['email'] == ['Email already in use']

    user = User.objects.get()  # still only one user
    assert user.name() == "Joe Doe"
    assert user.user.email == 'joedoe@example.com'

    # activate user so we can log in
    user.user.is_active = True
    user.user.save()

    # check if we can login with lowercase
    login_url = reverse('login')

    def check_login(email):
        response = client.post(
            login_url, {
                'email': email,
                'password': 'password',
                'i_accept_privacy_policy': True,
            }
        )
        # redirect means successful login, 200 means errors on form
        LOGIN_SUCCESFUL_302 = 302
        assert response.status_code == LOGIN_SUCCESFUL_302
        return True

    # the emails will be lowercased in db, but user is still able to log in
    # using whatever case they want
    assert check_login(email='JoeDoe@example.com')
    assert check_login(email='joedoe@example.com')
    assert check_login(email='JoeDoe@example.com')
    assert check_login(email='JOEDOE@example.com')
