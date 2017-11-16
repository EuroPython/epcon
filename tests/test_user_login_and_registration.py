# coding: utf-8

from __future__ import unicode_literals, absolute_import

from pytest import mark

from django.core.urlresolvers import reverse

from email_template.models import Email

from assopy.models import User

from tests.common_tools import (
    create_homepage_in_cms,
    template_used
)


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

    # TODO/FIXME: make it something like account/new_account.html
    # (maybe using django-allauth)
    assert template_used(response, "assopy/new_account.html")
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

    user = User.objects.get()
    assert user.name() == "Joe Doe"
    assert response.status_code == 200

    assert not user.user.is_active

    is_logged_in = client.login(email="joedoe@example.com",
                                password='password')
    assert not is_logged_in  # user is inactive

    response = client.get('/', follow=True)  # will redirect to /en/
    assert response.status_code == 200
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
    assert response.status_code == 200
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
    })
    assert response.status_code == 303

    user = User.objects.get()
    assert user.name() == "Joe Doe"
    assert user.user.email == 'joedoe@example.com'

    response = client.post(sign_up_url, {
        'first_name': 'Joe',
        'last_name': 'Doe',
        'email': 'jOEdOE@example.com',
        'password1': 'password',
        'password2': 'password',
    })
    assert response.status_code == 200
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
            login_url, {'email': email, 'password': 'password'}
        )
        # redirect means successful login, 200 means errors on form
        assert response.status_code == 302
        return True

    # the emails will be lowercased in db, but user is still able to log in
    # using whatever case they want
    assert check_login(email='JoeDoe@example.com')
    assert check_login(email='joedoe@example.com')
    assert check_login(email='JoeDoe@example.com')
    assert check_login(email='JOEDOE@example.com')
