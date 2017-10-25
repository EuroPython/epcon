# coding: utf-8

from __future__ import unicode_literals, absolute_import

from pytest import mark
from cms.api import create_page

from django.conf import settings
from django.utils import timezone

from email_template.models import Email

from assopy.models import User
from conference.models import Conference


def template_used(response, template_name):
    """
    TODO: this is a temporary location for this helper, move to a more
    appropriate location later on, when we have more test modules.
    """
    return template_name in [t.name for t in response.templates if t.name]


@mark.django_db
def test_user_registration(client):
    """
    Tests if users can create new account on the website
    (to buy tickets, etc).
    """
    # 1. test if user can create new account
    sign_up_url = "/accounts/new-account/"
    response = client.get(sign_up_url)
    assert response.status_code == 200
    # TODO/FIXME: change this template to something like
    # account/new_account.html (maybe using django-allauth)
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

    # 2. test if this new user can log in
    # Need to create conference before creating pages
    Conference.objects.get_or_create(code=settings.CONFERENCE_CONFERENCE,
                                     name=settings.CONFERENCE_CONFERENCE)
    create_page(title='HOME', template='django_cms/p5_homepage.html',
                language='en', reverse_id='home', published=True,
                publication_date=timezone.now())

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
