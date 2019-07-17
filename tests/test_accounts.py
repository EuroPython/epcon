from django.contrib.sites.shortcuts import get_current_site
from django.core import mail
from django.test.client import RequestFactory
from django_factory_boy import auth as auth_factories
from pytest import mark

from conference.accounts import send_verification_email


@mark.django_db
def test_send_verification_email():
    user = auth_factories.UserFactory()
    
    user.is_active = False
    user.save()

    request = RequestFactory()
    current_site = get_current_site(request)

    assert not mail.outbox  # sanity check

    send_verification_email(user, current_site)

    assert len(mail.outbox) == 1

    message = mail.outbox[0]
    assert len(message.recipients()) == 1
    assert message.recipients()[0] == user.email
    assert current_site.domain in message.body
