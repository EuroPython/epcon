# coding: utf-8

from __future__ import unicode_literals

from datetime import date
# from httplib import OK as HTTP_OK_200

from pytest import mark
from django.conf import settings
from django.core.urlresolvers import reverse

from django_factory_boy import auth as auth_factories
from freezegun import freeze_time

from assopy.models import Vat, Order
from assopy.tests.factories.user import UserFactory as AssopyUserFactory
from conference.fares import (
    pre_create_typical_fares_for_conference,
    set_early_bird_fare_dates,
    set_regular_fare_dates,
    SOCIAL_EVENT_FARE_CODE
)
from conference.models import Fare, AttendeeProfile

# from tests.common_tools import template_used  # , serve


DEFAULT_VAT_RATE = "0.2"  # 20%


def make_user():
    user = auth_factories.UserFactory(
        email='joedoe@example.com', is_active=True
    )
    AssopyUserFactory(user=user)
    AttendeeProfile.objects.create(user=user, slug='foobar')


def make_basic_fare_setup():
    assert Fare.objects.all().count() == 0
    conference_str = settings.CONFERENCE_CONFERENCE
    default_vat_rate, _ = Vat.objects.get_or_create(value=DEFAULT_VAT_RATE)
    pre_create_typical_fares_for_conference(conference_str, default_vat_rate)

    # Using some totally random dates just to test early vs regular in cart
    set_early_bird_fare_dates(conference_str,
                              date(2018, 3, 10), date(2018, 3, 12))

    set_regular_fare_dates(conference_str,
                           date(2018, 3, 20), date(2018, 6, 30))

    SOCIAL = Fare.objects.get(code=SOCIAL_EVENT_FARE_CODE)
    SOCIAL.start_validity = date(2018, 6, 20)
    SOCIAL.end_validity   = date(2018, 7, 30)
    SOCIAL.save()
    assert Fare.objects.all().count() == 28  # 3**3 + social event


@mark.django_db
def test_basic_fare_setup(client):
    make_user()
    make_basic_fare_setup()

    client.login(email='joedoe@example.com', password='password123')
    cart_url = reverse('p3-cart')

    with freeze_time("2018-02-11"):
        response = client.get(cart_url)
        _response_content = response.content.decode('utf-8')
        assert 'Sorry, no tickets are available' in _response_content

    with freeze_time("2018-03-11"):
        # Early Bird timeline
        response = client.get(cart_url)
        _response_content = response.content.decode('utf-8')
        assert 'TESP' in _response_content
        assert 'TEDC' in _response_content
        assert 'TRSP' not in _response_content
        assert 'TRDC' not in _response_content
        assert SOCIAL_EVENT_FARE_CODE not in _response_content

    with freeze_time("2018-05-11"):
        # Regular timeline
        response = client.get(cart_url)
        _response_content = response.content.decode('utf-8')
        assert 'TESP' not in _response_content
        assert 'TEDC' not in _response_content
        assert 'TRSP' in _response_content
        assert 'TRDC' in _response_content
        assert SOCIAL_EVENT_FARE_CODE not in _response_content

    with freeze_time("2018-06-25"):
        # Regular timeline
        response = client.get(cart_url)
        _response_content = response.content.decode('utf-8')
        assert 'TESP' not in _response_content
        assert 'TRSP' in _response_content
        assert 'TRDC' in _response_content
        assert SOCIAL_EVENT_FARE_CODE in _response_content


@mark.django_db
def test_buying_early_bird_only_during_early_bird_window(client):
    make_user()
    make_basic_fare_setup()

    client.login(email='joedoe@example.com', password='password123')
    cart_url = reverse('p3-cart')

    PURCHASE_SUCCESSFUL_302 = 302

    with freeze_time("2018-03-11"):
        # Early Bird timeline
        response = client.get(cart_url)
        _response_content = response.content.decode('utf-8')
        assert 'TESP' in _response_content
        assert 'TEDC' in _response_content

        assert Order.objects.all().count() == 0
        response = client.post(cart_url,
                               {'order_type': 'deductible', 'TESP': 1})
        assert response.status_code == PURCHASE_SUCCESSFUL_302
        # Purchase was successful but it's only first step, so still no Order
        assert Order.objects.all().count() == 0
