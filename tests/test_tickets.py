# coding: utf-8

from __future__ import unicode_literals

from datetime import date
# from httplib import OK as HTTP_OK_200

from pytest import mark
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone

# from django_factory_boy import auth as auth_factories
from freezegun import freeze_time
import responses

from assopy.models import Vat, Order, Country, Refund, Invoice
# from assopy.tests.factories.user import UserFactory as AssopyUserFactory
from conference.fares import (
    pre_create_typical_fares_for_conference,
    set_early_bird_fare_dates,
    set_regular_fare_dates,
    SOCIAL_EVENT_FARE_CODE
)
from conference import invoicing
from conference.currencies import (
    DAILY_ECB_URL,
    EXAMPLE_ECB_DAILY_XML,
    fetch_and_store_latest_ecb_exrates,
)
from conference.models import Conference, Fare, Ticket
from p3.models import TicketConference
from email_template.models import Email

from tests.common_tools import make_user


DEFAULT_VAT_RATE = "0.2"  # 20%

# TODO - this should be defined somewhere around the models.
DEFAULT_SHIRT_SIZE        = 'l'
DEFAULT_DIET              = 'omnivorous'
DEFAULT_PYTHON_EXPERIENCE = 0

# TODO/NOTE(artcz)(2018-06-26) – We use this for settings, but we should
# actually implement two sets of tests – one for full placeholder behaviour and
# one for non-placeholder behaviour.
invoicing.FORCE_PLACEHOLDER = True


def make_basic_fare_setup():
    assert Fare.objects.all().count() == 0
    conference_str = settings.CONFERENCE_CONFERENCE

    Conference.objects.get_or_create(
        code=conference_str,
        name=conference_str,
        # using 2018 dates
        # those dates are required for Tickets to work.
        # (for setting up/rendering attendance days)
        conference_start=date(2018, 7, 23),
        conference_end  =date(2018, 7, 29)
    )
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
        assert 'Buy tickets (1 of 2)' in _response_content

    with freeze_time("2018-03-11"):
        # Early Bird timeline
        response = client.get(cart_url)
        _response_content = response.content.decode('utf-8')
        assert 'data-fare="TESP"' in _response_content
        assert 'data-fare="TEDC"' in _response_content
        assert 'data-fare="TRSP"' not in _response_content
        assert 'data-fare="TRDC"' not in _response_content
        assert SOCIAL_EVENT_FARE_CODE not in _response_content
        assert 'Buy tickets (1 of 2)' in _response_content

    with freeze_time("2018-05-11"):
        # Regular timeline
        response = client.get(cart_url)
        _response_content = response.content.decode('utf-8')
        assert 'data-fare="TESP"' not in _response_content
        assert 'data-fare="TEDC"' not in _response_content
        assert 'data-fare="TRSP"' in _response_content
        assert 'data-fare="TRDC"' in _response_content
        assert SOCIAL_EVENT_FARE_CODE not in _response_content
        assert 'Buy tickets (1 of 2)' in _response_content

    with freeze_time("2018-06-25"):
        # Regular timeline
        response = client.get(cart_url)
        _response_content = response.content.decode('utf-8')
        assert 'data-fare="TESP"' not in _response_content
        assert 'data-fare="TRSP"' in _response_content
        assert 'data-fare="TRDC"' in _response_content
        assert SOCIAL_EVENT_FARE_CODE in _response_content
        assert 'Buy tickets (1 of 2)' in _response_content


# Same story as previously - using TestCase beacuse of django's asserts like
# assertRedirect even though it's run via pytest
class TestBuyingTickets(TestCase):

    def setUp(self):
        self.user = make_user()
        make_basic_fare_setup()
        with responses.RequestsMock() as rsps:
            # mocking responses for the invoice VAT exchange rate feature
            rsps.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
            fetch_and_store_latest_ecb_exrates()

    def test_buying_early_bird_only_during_early_bird_window(self):

        assert Ticket.objects.all().count() == 0
        # need to create an email template that's used in the purchasing
        # process
        Email.objects.create(code='purchase-complete')
        # and we need another email to reassign the ticket
        Email.objects.create(code='ticket-assigned')

        cart_url = reverse('p3-cart')
        billing_url = reverse('p3-billing')
        my_profile_url = reverse('assopy-profile')
        tickets_url = reverse('assopy-tickets')
        p3_tickets_url = reverse('p3-tickets')

        PURCHASE_FAILED_200     = 200
        PURCHASE_SUCCESSFUL_302 = 302

        with freeze_time("2018-03-11"):
            # need to relogin everytime we timetravel
            self.client.login(email='joedoe@example.com',
                              password='password123')
            # Early Bird timeline
            response = self.client.get(cart_url)
            _response_content = response.content.decode('utf-8')
            assert 'data-fare="TESP"' in _response_content
            assert 'data-fare="TEDC"' in _response_content
            assert 'Buy tickets (1 of 2)' in _response_content

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
            self.assertContains(response, 'Buy tickets (2 of 2)')
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
            assert TicketConference.objects.all().count() == 3

            response = self.client.get(my_profile_url, follow=True)
            # This is not visible because you need to confirm order for this to
            # work.
            self.assertNotContains(response, 'View your tickets')
            self.assertNotContains(response, tickets_url)

            order = Order.objects.get()
            assert order.total() == 630  # because 210 per ticket
            assert not order._complete

            order.confirm_order(date.today())
            assert order._complete

            invoice = Invoice.objects.get()
            assert invoice.html == invoicing.VAT_NOT_AVAILABLE_PLACEHOLDER

            response = self.client.get(my_profile_url)
            self.assertContains(response, 'View your tickets (3)')
            self.assertContains(response, tickets_url)
            self.assertContains(response,
                                invoicing.VAT_NOT_AVAILABLE_PLACEHOLDER)

            response = self.client.get(p3_tickets_url)
            latest_ticket = Ticket.objects.latest('id')
            ticket_url = reverse('p3-ticket', kwargs={'tid': latest_ticket.id})
            self.assertContains(response, ticket_url)

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

        # and then test assigning the tickets
        self.client.login(email='joedoe@example.com', password='password123')
        response = self.client.get(tickets_url, follow=True)
        self.assertRedirects(response, p3_tickets_url)


# defaulting to date when regular tickets are being sold
@freeze_time("2018-05-11")
class TestTicketManagementScenarios(TestCase):

    def setUp(self):
        """
        We're going to replay some of the setup from the previous test here,
        including buying tickets via test client, instead of just creating them
        through the factory – just to make sure we're definitely in the same
        setup as typical user of the website.
        """
        self.user = make_user()
        make_basic_fare_setup()
        with responses.RequestsMock() as rsps:
            # mocking responses for the invoice VAT exchange rate feature
            rsps.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
            fetch_and_store_latest_ecb_exrates()

        Email.objects.create(code='purchase-complete')
        Email.objects.create(code='ticket-assigned')
        Email.objects.create(code='refund-credit-note')

        self.cart_url = reverse('p3-cart')
        self.billing_url = reverse('p3-billing')
        self.my_profile_url = reverse('assopy-profile')
        self.tickets_url = reverse('assopy-tickets')
        self.p3_tickets_url = reverse('p3-tickets')

        self.client.login(email='joedoe@example.com', password='password123')
        PURCHASE_SUCCESSFUL_302 = 302

        assert Order.objects.all().count() == 0
        response = self.client.post(self.cart_url, {
            'order_type': 'deductible',
            'TRSP': 3,
        }, follow=True)

        self.assertRedirects(response, self.billing_url,
                             status_code=PURCHASE_SUCCESSFUL_302)
        # Purchase was successful but it's first step, so still no Order
        assert Order.objects.all().count() == 0

        Country.objects.create(iso='PL', name='Poland')
        response = self.client.post(self.billing_url, {
            'card_name': 'Joe Doe',
            'payment': 'cc',
            'country': 'PL',
            'address': 'Random 42',
            'cf_code': '31447',
            'code_conduct': True,
        })
        assert response.status_code == PURCHASE_SUCCESSFUL_302
        assert Order.objects.all().count() == 1
        self.order = Order.objects.get()
        self.ticket = Ticket.objects.latest('id')
        self.ticket_url = reverse('p3-ticket', kwargs={'tid': self.ticket.id})
        # p3_conference is associated TicketConference instance
        self.tc = self.ticket.p3_conference

        self.VALIDATION_SUCCESSFUL_200 = 200
        self.VALIDATION_ERROR_400      = 400
        self.MAIN_USER_EMAIL  = self.user.email
        self.OTHER_USER_EMAIL = 'foobar@example.com'

        with responses.RequestsMock() as rsps:
            # mocking responses for the invoice VAT exchange rate feature
            rsps.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
            fetch_and_store_latest_ecb_exrates()

    def prefix(self, fieldname):
        """For some reason the website is using prefixed fields...
        And the prefix has to match the ticket we're trying to modify.
        """
        return "t%s-%s" % (self.ticket.id, fieldname)

    def test_simple_GET(self):
        response = self.client.get(self.ticket_url)
        self.assertTemplateUsed(response, "p3/fragments/render_ticket.html")

    def test_assign_ticket_to_another_user(self):
        response = self.client.post(self.ticket_url, {
            # This is the only field we're interested in
            self.prefix('assigned_to'): self.OTHER_USER_EMAIL,

            # but all the other fields are required.
            self.prefix('python_experience'): 3,
            self.prefix('diet'):             'vegetarian',
            self.prefix('shirt_size'):       'xl',
        })
        assert response.status_code == self.VALIDATION_SUCCESSFUL_200
        self.tc.refresh_from_db()
        assert self.tc.assigned_to == self.OTHER_USER_EMAIL
        # other values stay as default because after (re)assigning it resets
        # all the ticket options
        assert self.tc.diet              == DEFAULT_DIET
        assert self.tc.shirt_size        == DEFAULT_SHIRT_SIZE
        assert self.tc.python_experience == DEFAULT_PYTHON_EXPERIENCE

        # also make sure that after assigning the ticket you can't modify it
        response = self.client.post(self.ticket_url, {
            # but all the other fields are required.
            self.prefix('python_experience'): 5,
            self.prefix('diet'):             'other',
            self.prefix('shirt_size'):       'fm',
        })

        self.tc.refresh_from_db()
        assert self.tc.diet              == DEFAULT_DIET
        assert self.tc.shirt_size        == DEFAULT_SHIRT_SIZE
        assert self.tc.python_experience == DEFAULT_PYTHON_EXPERIENCE

    def test_assign_ticket_to_another_user_case_insensitive(self):
        # we need to confirm the order for the tickets to display in the profile
        self.order.confirm_order(date.today())

        other_user = make_user(self.OTHER_USER_EMAIL)

        response = self.client.post(self.ticket_url, {
            # This is the only field we're interested in
            self.prefix('assigned_to'): self.OTHER_USER_EMAIL.upper(),

            # but all the other fields are required.
            self.prefix('python_experience'): 3,
            self.prefix('diet'):             'vegetarian',
            self.prefix('shirt_size'):       'xl',
        })
        assert response.status_code == self.VALIDATION_SUCCESSFUL_200
        self.tc.refresh_from_db()
        # only care about case insensitive match
        assert self.tc.assigned_to.lower() == self.OTHER_USER_EMAIL.lower()

        # switch user
        self.client.login(email=self.OTHER_USER_EMAIL, password='password123')
        self.tc.refresh_from_db()

        response = self.client.get(self.my_profile_url)
        self.assertContains(response, 'View your tickets')
        self.assertContains(response, self.tickets_url)

        # Check that ticket is visible
        response = self.client.get(self.p3_tickets_url)
        self.assertContains(response, self.ticket_url)

        # And that it has an "Edit this ticket"
        self.assertContains(response, "Edit this ticket")

        # Check that it can be edited
        # defaults
        assert self.tc.assigned_to.lower() == self.OTHER_USER_EMAIL.lower()
        assert self.tc.diet              == DEFAULT_DIET
        assert self.tc.shirt_size        == DEFAULT_SHIRT_SIZE
        assert self.tc.python_experience == DEFAULT_PYTHON_EXPERIENCE

        response = self.client.post(self.ticket_url, {
            # Looks liek assigned_to is a mandatory requirement as well, w/o it
            # it would pass the validation but not save the results inside TC.
            # possible FIXME(?)
            self.prefix('assigned_to'):       self.OTHER_USER_EMAIL.upper(),
            self.prefix('python_experience'): 5,
            self.prefix('diet'):             'other',
            self.prefix('shirt_size'):       'fm',
        })
        assert response.status_code == self.VALIDATION_SUCCESSFUL_200

        self.tc.refresh_from_db()
        assert self.tc.assigned_to.lower() == self.OTHER_USER_EMAIL.lower()
        assert self.tc.diet              == 'other'
        assert self.tc.shirt_size        == 'fm'
        assert self.tc.python_experience == 5



    def test_reclaim_ticket(self):
        assert self.tc.assigned_to == self.MAIN_USER_EMAIL
        self.client.post(self.ticket_url, {
            self.prefix('assigned_to'): self.OTHER_USER_EMAIL,

            # but all the other fields are required.
            self.prefix('python_experience'): 3,
            self.prefix('diet'):             'vegetarian',
            self.prefix('shirt_size'):       'xl',
        })

        self.tc.refresh_from_db()
        assert self.tc.assigned_to == self.OTHER_USER_EMAIL

        self.client.post(self.ticket_url, {
            self.prefix('assigned_to'):       '',

            # but all the other fields are required.
            self.prefix('python_experience'): 3,
            self.prefix('diet'):             'vegetarian',
            self.prefix('shirt_size'):       'xl',
        })

        self.tc.refresh_from_db()
        assert self.tc.assigned_to == self.MAIN_USER_EMAIL

    def test_modify_your_ticket(self):
        # defaults
        assert self.tc.assigned_to       == self.MAIN_USER_EMAIL
        assert self.tc.diet              == DEFAULT_DIET
        assert self.tc.shirt_size        == DEFAULT_SHIRT_SIZE
        assert self.tc.python_experience == DEFAULT_PYTHON_EXPERIENCE

        response = self.client.post(self.ticket_url, {
            # Looks liek assigned_to is a mandatory requirement as well, w/o it
            # it would pass the validation but not save the results inside TC.
            # possible FIXME(?)
            self.prefix('assigned_to'):       self.MAIN_USER_EMAIL,
            self.prefix('python_experience'): 5,
            self.prefix('diet'):             'other',
            self.prefix('shirt_size'):       'fm',
        })
        assert response.status_code == self.VALIDATION_SUCCESSFUL_200

        self.tc.refresh_from_db()
        assert self.tc.assigned_to       == self.MAIN_USER_EMAIL
        assert self.tc.diet              == 'other'
        assert self.tc.shirt_size        == 'fm'
        assert self.tc.python_experience == 5

        # not having assigned_to in the form, even if the ticket is already
        # assigned to the user, will cause reset of the ticket
        # potential FIXME as well.
        response = self.client.post(self.ticket_url, {
            self.prefix('python_experience'): 4,
            self.prefix('diet'):             'vegetarian',
            self.prefix('shirt_size'):       'fxxl',
        })
        assert response.status_code == self.VALIDATION_SUCCESSFUL_200

        self.tc.refresh_from_db()
        assert self.tc.assigned_to       == self.MAIN_USER_EMAIL
        assert self.tc.diet              == DEFAULT_DIET
        assert self.tc.shirt_size        == DEFAULT_SHIRT_SIZE
        assert self.tc.python_experience == DEFAULT_PYTHON_EXPERIENCE

    def test_invalid_data_returns_an_error(self):
        # reassign to someone else and it *will* reset the ticket.
        # even if the keys are present in the POST. beware.
        # BUT, despite that the changes will be reset, it will still do the
        # full validation and fail on the wrong diet type.
        # and because of that validation error the ticket will not be
        # reassigned too.
        response = self.client.post(self.ticket_url, {
            self.prefix('assigned_to'):       self.OTHER_USER_EMAIL,
            self.prefix('python_experience'): 3,
            self.prefix('diet'):              'only-candy',
            self.prefix('shirt_size'):        'xl',
        })
        assert response.status_code == self.VALIDATION_ERROR_400

        self.assertContains(response,
                            'only-candy is not one of the available choices',
                            status_code=self.VALIDATION_ERROR_400)

        self.tc.refresh_from_db()
        assert self.tc.assigned_to       == self.MAIN_USER_EMAIL
        assert self.tc.diet              == DEFAULT_DIET
        assert self.tc.shirt_size        == DEFAULT_SHIRT_SIZE
        assert self.tc.python_experience == DEFAULT_PYTHON_EXPERIENCE

    def test_refund_tickets(self):
        assert Refund.objects.all().count() == 0
        assert not self.ticket.frozen
        with self.assertRaises(AssertionError):
            # it raises assertion error because we don't refund unpaid orders
            self.client.post(self.ticket_url, {'refund': 'asdf'})

        assert Invoice.objects.all().count() == 0

        self.order.confirm_order(timezone.now().date())

        assert Invoice.objects.all().count() == 1

        self.client.post(self.ticket_url, {'refund': 'asdf'})

        assert Refund.objects.all().count() == 1
        refund = Refund.objects.get()
        assert refund.status == 'pending'

        self.ticket.refresh_from_db()
        assert self.ticket.frozen

        # refunds work via save() and some signals
        refund.status = 'rejected'
        refund.save()

        self.ticket.refresh_from_db()
        # ticket is suddenly unfrozen
        assert not self.ticket.frozen

        refund.status = 'refunded'
        refund.save()

        with self.assertRaises(Ticket.DoesNotExist):
            # if refund is refunded it deletes the ticket associated with this
            # refund.
            self.ticket.refresh_from_db()
