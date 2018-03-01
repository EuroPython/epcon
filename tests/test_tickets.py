# coding: utf-8

from __future__ import unicode_literals

from datetime import date
# from httplib import OK as HTTP_OK_200

from pytest import mark
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase

from django_factory_boy import auth as auth_factories
from freezegun import freeze_time

from assopy.models import Vat, Order, Country
from assopy.tests.factories.user import UserFactory as AssopyUserFactory
from conference.fares import (
    pre_create_typical_fares_for_conference,
    set_early_bird_fare_dates,
    set_regular_fare_dates,
    SOCIAL_EVENT_FARE_CODE
)
from conference.models import Conference, Fare, AttendeeProfile, Ticket
from email_template.models import Email

# from tests.common_tools import serve


DEFAULT_VAT_RATE = "0.2"  # 20%


def make_user():
    user = auth_factories.UserFactory(
        email='joedoe@example.com', is_active=True
    )
    AssopyUserFactory(user=user)
    AttendeeProfile.objects.create(user=user, slug='foobar')
    return user


def make_basic_fare_setup():
    assert Fare.objects.all().count() == 0
    conference_str = settings.CONFERENCE_CONFERENCE

    Conference.objects.get_or_create(code=conference_str,
                                     name=conference_str)
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


# Same story as previously - using TestCase beacuse of django's asserts like
# assertRedirect even though it's run via pytest
class TestBuyingTickets(TestCase):

    def setUp(self):
        self.user = make_user()
        make_basic_fare_setup()

    def test_buying_early_bird_only_during_early_bird_window(self):

        assert Ticket.objects.all().count() == 0
        # need to create an email template that's used in the purchasing
        # process
        Email.objects.create(code='purchase-complete')

        cart_url = reverse('p3-cart')
        billing_url = reverse('p3-billing')

        PURCHASE_FAILED_200     = 200
        PURCHASE_SUCCESSFUL_302 = 302

        with freeze_time("2018-03-11"):
            # need to relogin everytime we timetravel
            self.client.login(email='joedoe@example.com',
                              password='password123')
            # Early Bird timeline
            response = self.client.get(cart_url)
            _response_content = response.content.decode('utf-8')
            assert 'TESP' in _response_content
            assert 'TEDC' in _response_content

            assert Order.objects.all().count() == 0
            response = self.client.post(cart_url, {
                'order_type': 'deductible',
                'TESP': 3,
                # TODO/FIXME(?)
                # Looks like adding unavailable types (in this case TRSP, which
                # already exists but is scheduled to be avilable in some later
                # time) doesn't cause any problems – it just doesn't create
                # tickets of that type.
                # Maybe it should return some error message in such case?
                'TRSP': 2
            }, follow=True)

            self.assertRedirects(response, billing_url,
                                 status_code=PURCHASE_SUCCESSFUL_302)
            # Purchase was successful but it's first step, so still no Order
            assert Order.objects.all().count() == 0

            Country.objects.create(iso='PL', name='Poland')
            response = self.client.post(billing_url, {
                'card_name': 'Joe Doe',
                'payment': 'cc',
                'country': 'PL',
                'address': 'Random 42',
                'cf_code': '31447',
                'code_conduct': True,
            })
            assert response.status_code == PURCHASE_SUCCESSFUL_302

            stripe_checkout_url = '/accounts/stripe/checkout/1/'
            self.assertRedirects(response, stripe_checkout_url)

            # after payment order is created
            assert Order.objects.all().count() == 1
            # tickets are created even if Order is not yet `confirmed`.
            assert Ticket.objects.all().count() == 3

            my_profile_url = reverse('assopy-profile')
            response = self.client.get(my_profile_url, follow=True)
            # This is not visible because you need to confirm order for this to
            # work.
            self.assertNotContains(response, 'View your tickets')

            order = Order.objects.get()
            assert order.total() == 3000
            assert not order._complete
            order.confirm_order(date.today())
            assert order._complete

            response = self.client.get(my_profile_url)
            self.assertContains(response, 'View your tickets (3)')

        with freeze_time("2018-05-11"):
            # need to relogin everytime we timetravel
            self.client.login(email='joedoe@example.com',
                              password='password123')
            response = self.client.post(cart_url, {
                'order_type': 'deductible',
                'TESP': 3,  # more early birds
            })
            assert response.status_code == PURCHASE_FAILED_200
            assert response.context['form'].errors['__all__'] == ['No tickets']
