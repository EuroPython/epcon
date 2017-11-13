# coding: utf-8

from __future__ import unicode_literals, absolute_import

from datetime import date, timedelta
from decimal import Decimal

from pytest import mark

from django.core.urlresolvers import reverse
from django.conf import settings

from django_factory_boy import auth as auth_factories
from freezegun import freeze_time

from assopy.models import Country, Invoice, Order, Vat, VatFare
from assopy.tests.factories.user import UserFactory as AssopyUserFactory
from conference.models import AttendeeProfile, Fare, Ticket
from conference import settings as conference_settings
from email_template.models import Email

from tests.common_tools import template_used, sequence_equals, serve  # NOQA


@mark.django_db
def test_592_dont_display_invoices_for_yeras_before_2018(client):
    """
    https://github.com/EuroPython/epcon/issues/592

    Temporary(?) test for #592, until #591 is fixed.
    """

    # default password is 'password123' per django_factory_boy
    user = auth_factories.UserFactory(email='joedoe@example.com',
                                      is_active=True)

    # both are required to access user profile page.
    assopy_user = AssopyUserFactory(user=user)
    AttendeeProfile.objects.create(user=user, slug='foobar')

    client.login(email='joedoe@example.com', password='password123')

    # create some random Vat instance to the invoice creation works
    vat_10 = Vat.objects.create(value=10)

    # invoice_code must be validated via ASSOPY_IS_REAL_INVOICE
    invoice_code_2017, order_code_2017 = 'I2017', 'O2017'
    invoice_code_2018, order_code_2018 = 'I2018', 'O2018'

    order2017 = Order(user=assopy_user, code=order_code_2017)
    order2017.save()
    order2017.created = date(2017, 12, 31)
    order2017.save()

    order2018 = Order(user=assopy_user, code=order_code_2018)
    order2018.save()
    order2018.created = date(2018, 1, 1)
    order2018.save()

    Invoice.objects.create(
        code=invoice_code_2017,
        order=order2017,
        emit_date=date(2017, 3, 13),
        price=Decimal(1337),
        vat=vat_10,
    )

    # Doesn't matter when the invoice was issued (invoice.emit_date),
    # it only matters what's the Order.created date
    Invoice.objects.create(
        code=invoice_code_2018,
        order=order2018,
        emit_date=date(2017, 3, 13),
        price=Decimal(1337),
        vat=vat_10,
    )

    user_profile_url = reverse("assopy-profile")
    response = client.get(user_profile_url)

    assert invoice_code_2017 not in response.content.decode('utf-8')
    assert order_code_2017 not in response.content.decode('utf-8')

    assert invoice_code_2018 in response.content.decode('utf-8')
    assert order_code_2018 in response.content.decode('utf-8')

    assert reverse("assopy-invoice-html", kwargs={
        'code': invoice_code_2018,
        'order_code': order_code_2018,
    }) in response.content.decode('utf-8')

    assert template_used(response, 'assopy/profile.html')


@mark.django_db
@freeze_time("2018-01-01")
def test_invoices_from_buying_tickets(client):
    """
    This is an example of a full flow, of creating and buying a new ticket.
    """

    assert settings.P3_FARES_ENABLED

    # 1. First create a user with complete profile.
    # default password is 'password123' per django_factory_boy
    user = auth_factories.UserFactory(email='joedoe@example.com',
                                      is_active=True)

    # both are required to access user profile page.
    AssopyUserFactory(user=user)
    AttendeeProfile.objects.create(user=user, slug='foobar')

    client.login(email='joedoe@example.com', password='password123')

    # 2. Let's start with checking if no tickets are available at first
    cart_url = reverse('p3-cart')
    response = client.get(cart_url)
    assert template_used(response, "p3/cart.html")
    assert 'Sorry, no tickets are available' in response.content

    # 3. p3/cart.html is using {% fares_available %} assignment tag
    # lets create some fares.
    # just setting a single type of ticket, for testing. In reality there are
    # 27 possible fare types for just the tickets
    #   (early bird, regular, on desk)
    # x (standard, stndard light, day pass)
    # x (student, personal, company)

    # fare_codes = [
    #     'T' + ticket_type + ticket_variant + group_type
    #     # E = Early Bird, R = Regular, D = on Desk
    #     for ticket_type in ['E', 'R', 'D']
    #     # S = Standard; L = Standard Light (no trainings); D = Day Pass
    #     for ticket_variant in ['S', 'L', 'D']
    #     # S = Student; P = Personal; C = Company
    #     for group_type in ['S', 'P', 'C']
    # ]

    ticket_price = 100
    ticket_amount = 20
    social_event_price = 10
    social_event_amount = 5

    def create_fare(code, price, name, type, vat_rate):
        # TODO: maybe use Fare factory(?)
        fare = Fare.objects.create(
            conference=settings.CONFERENCE_CONFERENCE,
            name=name,
            description=name,
            code=code,
            price=price,
            ticket_type=type,
            start_validity=date.today() - timedelta(days=10),
            end_validity=date.today() + timedelta(days=10),
        )

        # fare also needs VAT
        vat_rate, _ = Vat.objects.get_or_create(value=vat_rate)
        VatFare.objects.get_or_create(fare=fare, vat=vat_rate)
        return fare

    create_fare("TRSP",  # Ticket Regular Standard Personal
                ticket_price,
                "Regular Standard Ticket",
                "conference",
                vat_rate=10)

    create_fare("VOUPE03",  # hardcoded social event format
                social_event_price,
                "Social Event One",
                "event",
                vat_rate=10)

    create_fare("S123",  # some random social event id
                social_event_price,
                "Social Event Two",
                "other",
                vat_rate=20)

    # 4. If Fare is created we should have one input on the cart.
    response = client.get(cart_url)
    assert template_used(response, "p3/cart.html")
    _response_content = response.content.decode('utf-8')

    assert 'Sorry, no tickets are available' not in _response_content
    assert 'Buy tickets (1 of 2)' in _response_content

    # There are plenty of tds but only TRSP should have data-fare set
    assert 'td class="fare" data-fare="TRSP">' in _response_content
    assert 'td class="fare" data-fare="TDCP">' not in _response_content
    assert 'td class="fare" data-fare="">' in _response_content
    # social events
    assert 'td class="fare" data-fare="VOUPE03">' in _response_content
    assert 'td class="fare" data-fare="S123">' in _response_content

    # and one input for TRSP where you can specify how many tickets
    # TODO: maybe it should have a different type than text?
    assert '<input type="text" size="2" name="TRSP"' in _response_content

    # 5. Try buying some tickets
    # FIXME: looks like the max_tickets is enforced only with javascript
    assert ticket_amount > conference_settings.MAX_TICKETS

    response = client.post(cart_url, {
        'order_type': 'non-deductible',  # == Personal
        'TRSP': ticket_amount,
        'VOUPE03': social_event_amount,
        'S123': social_event_amount,
    }, follow=True)

    billing_url = reverse('p3-billing')
    assert response.status_code == 200
    assert response.request['PATH_INFO'] == billing_url

    assert 'Buy tickets (2 of 2)' in response.content.decode('utf-8')

    # unless you POST to the billing page the Order is not created
    assert Order.objects.count() == 0

    Country.objects.create(iso='PL', name='Poland')
    response = client.post(billing_url, {
        'card_name': 'Joe Doe',
        'payment': 'cc',
        'country': 'PL',
        'address': 'Random 42',
        'cf_code': '31447',
        'code_conduct': True,
    }, follow=True)
    assert response.status_code == 200
    assert response.request['PATH_INFO'] == '/accounts/stripe/checkout/1/'

    order = Order.objects.get()
    # FIXME: confirming that max_tickets is only enforced in javascript
    assert order.orderitem_set.all().count() ==\
        ticket_amount + social_event_amount * 2  # two social events

    # need to create an email template that's used in the purchasing process
    Email.objects.create(code='purchase-complete')

    # no invoices
    assert Invoice.objects.all().count() == 0
    # static date, because of #592 choosing something in 2018
    order.confirm_order(date(2018, 1, 1))

    # multiple items per invoice, one invoice per vat rate.
    assert Invoice.objects.all().count() == 2

    invoice_vat_10 = Invoice.objects.get(vat__value=10)
    invoice_vat_20 = Invoice.objects.get(vat__value=20)

    # only one orderitem_set instance because they are grouped by fare_code
    # items are ordered desc by price.
    expected_invoice_items_vat_10 = [
        {'count': ticket_amount,
         'price': ticket_price * ticket_amount,
         'code': u'TRSP',
         'description': u'Regular Standard Ticket'},
        {'count': social_event_amount,
         'price': social_event_price * social_event_amount,
         'code': u'VOUPE03',
         'description': u'Social Event One'},
    ]

    expected_invoice_items_vat_20 = [
        {'count': social_event_amount,
         'price': social_event_price * social_event_amount,
         'code': u'S123',
         'description': u'Social Event Two'},
    ]

    assert sequence_equals(invoice_vat_10.invoice_items(),
                           expected_invoice_items_vat_10)
    assert sequence_equals(invoice_vat_20.invoice_items(),
                           expected_invoice_items_vat_20)

    # check numbers for vat 10%
    gross_price_vat_10 = (
        ticket_price * ticket_amount
        + social_event_price * social_event_amount
    )
    net_price_vat_10 = gross_price_vat_10 / Decimal('1.1')
    vat_value_vat_10 = gross_price_vat_10 - net_price_vat_10

    assert invoice_vat_10.price == gross_price_vat_10
    assert invoice_vat_10.net_price() == net_price_vat_10
    assert invoice_vat_10.vat_value() == vat_value_vat_10

    # do the same for vat 20%
    gross_price_vat_20 = social_event_price * social_event_amount
    net_price_vat_20 = gross_price_vat_20 / Decimal('1.2')
    vat_value_vat_20 = gross_price_vat_20 - net_price_vat_20

    assert invoice_vat_20.price == gross_price_vat_20
    assert invoice_vat_20.net_price() == net_price_vat_20
    assert invoice_vat_20.vat_value() == vat_value_vat_20

    # each OrderItem should have a corresponding Ticket
    assert Ticket.objects.all().count() ==\
        ticket_amount + social_event_amount * 2

    # Check if user profile has the tickets and invoices available
    profile_url = reverse('assopy-profile')
    response = client.get(profile_url)

    # order code depends on when this test is run, but invoice code should
    # default to whatever payment_date is (in this case 2018, 1, 1)
    # TODO: currently this test is under freezegun, but we may want to remove
    # it later and replace with APIs that allows to control/specify date for
    # order and invoice.
    assert 'O/18.0001' in response.content.decode('utf-8')
    # there is only one order but two invoices
    assert 'I/18.0001' in response.content.decode('utf-8')
    assert 'I/18.0002' in response.content.decode('utf-8')
