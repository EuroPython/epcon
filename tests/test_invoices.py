# coding: utf-8
from __future__ import unicode_literals, absolute_import

import csv
import decimal
from datetime import date, timedelta
from decimal import Decimal
import random

from django.http import QueryDict
from pytest import mark

from django.core.urlresolvers import reverse
from django.core.management import call_command
from django.conf import settings

from django_factory_boy import auth as auth_factories
from freezegun import freeze_time
import responses

from assopy.models import Country, Invoice, Order, Vat
from assopy.tests.factories.user import UserFactory as AssopyUserFactory
from assopy.stripe.tests.factories import FareFactory, OrderFactory
# from common.http import PdfResponse
from conference.models import AttendeeProfile, Ticket, Fare
from conference import settings as conference_settings
from conference import invoicing  # for monkey patching below
from conference.invoicing import (
    ACPYSS_16,
    PYTHON_ITALIA_17,
    EPS_18,
    VAT_NOT_AVAILABLE_PLACEHOLDER,
    upgrade_invoice_placeholder_to_real_invoice,
    # render_invoice_as_html,
)
from conference.currencies import (
    DAILY_ECB_URL,
    EXAMPLE_ECB_DAILY_XML,
    EXAMPLE_ECB_DATE,
    normalize_price,
    fetch_and_store_latest_ecb_exrates,
)
from conference.fares import (
    SOCIAL_EVENT_FARE_CODE,
    create_fare_for_conference,
    pre_create_typical_fares_for_conference,
)
from email_template.models import Email

from tests.common_tools import (  # NOQA
    template_used,
    sequence_equals,
    make_user,
    serve_response,
    serve_text
)

# TODO/NOTE(artcz)(2018-06-26) – We use this for settings, but we should
# actually implement two sets of tests – one for full placeholder behaviour and
# one for non-placeholder behaviour.
invoicing.FORCE_PLACEHOLDER = True


def _prepare_invoice_for_basic_test(order_code, invoice_code):
    # default password is 'password123' per django_factory_boy
    user = make_user()

    # FYI(artcz): Order.objects.create is overloaded method on
    # OrderManager, that sets up a lot of unused stuff, going with manual
    # .save().
    order = Order(user=user.assopy_user, code=order_code)
    order.save()
    # create some random Vat instance to the invoice creation works
    vat_10 = Vat.objects.create(value=10)

    Invoice.objects.create(
        code=invoice_code,
        order=order,
        emit_date=date.today(),
        price=Decimal(1337),
        vat=vat_10,
        html='<html>Here goes full html</html>',
        exchange_rate_date=date.today(),
    )


@mark.django_db
def test_invoice_html(client):
    # invoice_code must be validated via ASSOPY_IS_REAL_INVOICE
    invoice_code, order_code = 'I123', 'asdf'
    _prepare_invoice_for_basic_test(order_code, invoice_code)

    client.login(email='joedoe@example.com', password='password123')
    invoice_url = reverse('assopy-invoice-html', kwargs={
        'order_code': order_code,
        'code': invoice_code,
    })
    response = client.get(invoice_url)

    assert response.content == '<html>Here goes full html</html>'


@mark.django_db
def test_invoice_pdf(client):
    # invoice_code must be validated via ASSOPY_IS_REAL_INVOICE
    invoice_code, order_code = 'I123', 'asdf'
    _prepare_invoice_for_basic_test(order_code, invoice_code)

    client.login(email='joedoe@example.com', password='password123')
    invoice_url = reverse('assopy-invoice-pdf', kwargs={
        'order_code': order_code,
        'code': invoice_code,
    })

    response = client.get(invoice_url)
    assert response.status_code == 200
    assert response['Content-type'] == 'application/pdf'


@mark.django_db
def test_592_dont_display_invoices_for_years_before_2018(client):
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
        exchange_rate_date=date.today(),
    )

    # Doesn't matter when the invoice was issued (invoice.emit_date),
    # it only matters what's the Order.created date
    Invoice.objects.create(
        code=invoice_code_2018,
        order=order2018,
        emit_date=date(2017, 3, 13),
        price=Decimal(1337),
        vat=vat_10,
        exchange_rate_date=date.today(),
    )

    user_profile_url = reverse("assopy-profile")
    response = client.get(user_profile_url)

    assert invoice_code_2017 not in response.content.decode('utf-8')
    assert order_code_2017 not in response.content.decode('utf-8')

    assert invoice_code_2018 in response.content.decode('utf-8')
    assert order_code_2018 in response.content.decode('utf-8')

    assert reverse("assopy-invoice-pdf", kwargs={
        'code': invoice_code_2018,
        'order_code': order_code_2018,
    }) in response.content.decode('utf-8')

    assert template_used(response, 'assopy/profile.html')


@responses.activate
@mark.django_db
@freeze_time("2018-01-01")
def test_invoices_from_buying_tickets(client):
    """
    This is an example of a full flow, of creating and buying a new ticket.
    """
    # because of 2018 we need to make sure that ECB rates are in place
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
    fetch_and_store_latest_ecb_exrates()

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

    # 3. p3/cart.html is using {% fares_available %} assignment tag to display
    # fares.  For more details about fares check conference/fares.py

    ticket_price  = Decimal(100)
    ticket_amount = 20
    social_event_price  = Decimal(10)
    social_event_amount = 5

    vat_rate_10, _ = Vat.objects.get_or_create(value=10)
    vat_rate_20, _ = Vat.objects.get_or_create(value=20)

    today = date.today()
    yesterday, tomorrow = today - timedelta(days=1), today + timedelta(days=1)

    CONFERENCE = settings.CONFERENCE_CONFERENCE

    create_fare_for_conference(code="TRSP",  # Ticket Regular Standard Personal
                               conference=CONFERENCE,
                               price=ticket_price,
                               start_validity=yesterday,
                               end_validity=tomorrow,
                               vat_rate=vat_rate_10)

    create_fare_for_conference(code=SOCIAL_EVENT_FARE_CODE,
                               conference=CONFERENCE,
                               price=social_event_price,
                               start_validity=yesterday,
                               end_validity=tomorrow,
                               vat_rate=vat_rate_20)

    # 4. If Fare is created we should have one input on the cart.
    response = client.get(cart_url)
    assert template_used(response, "p3/cart.html")
    _response_content = response.content.decode('utf-8')

    assert 'Sorry, no tickets are available' not in _response_content
    assert 'Buy tickets (1 of 2)' in _response_content

    # There are plenty of tds but only TRSP should have data-fare set
    assert 'td class="fare" data-fare="TRSP">' in _response_content
    assert 'td class="fare" data-fare="TDCP">' not in _response_content
    assert 'td class="fare" data-fare="">'     in _response_content
    # social events
    assert 'td class="fare" data-fare="VOUPE03">' in _response_content

    # and one input for TRSP where you can specify how many tickets
    # TODO: maybe it should have a different type than text?
    assert '<input type="text" size="2" name="TRSP"' in _response_content

    # 5. Try buying some tickets
    # FIXME: looks like the max_tickets is enforced only with javascript
    assert ticket_amount > conference_settings.MAX_TICKETS

    response = client.post(cart_url, {
        'order_type': 'non-deductible',  # == Personal
        'TRSP':    ticket_amount,
        'VOUPE03': social_event_amount,
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
        ticket_amount + social_event_amount

    # need to create an email template that's used in the purchasing process
    Email.objects.create(code='purchase-complete')

    # no invoices
    assert Invoice.objects.all().count() == 0
    # static date, because of #592 choosing something in 2018
    SOME_RANDOM_DATE = date(2018, 1, 1)
    order.confirm_order(SOME_RANDOM_DATE)
    assert order.payment_date == SOME_RANDOM_DATE

    # # multiple items per invoice, one invoice per vat rate.
    # # 2 invoices but they are both placeholders
    assert Invoice.objects.all().count() == 2
    assert Invoice.objects.filter(
        html=VAT_NOT_AVAILABLE_PLACEHOLDER
    ).count() == 2

    # # and we can then upgrade all invoices to non-placeholders
    for _invoice in Invoice.objects.all():
        upgrade_invoice_placeholder_to_real_invoice(_invoice)

    assert Invoice.objects.all().count() == 2
    assert Invoice.objects.filter(
        html=VAT_NOT_AVAILABLE_PLACEHOLDER
    ).count() == 0

    invoice_vat_10 = Invoice.objects.get(vat__value=10)
    invoice_vat_20 = Invoice.objects.get(vat__value=20)

    # only one orderitem_set instance because they are grouped by fare_code
    # items are ordered desc by price.
    expected_invoice_items_vat_10 = [
        {'count': ticket_amount,
         'price': ticket_price * ticket_amount,
         'code': u'TRSP',
         'description': u'ep2018 - Regular Standard Personal'},
    ]

    expected_invoice_items_vat_20 = [
        {'count': social_event_amount,
         'price': social_event_price * social_event_amount,
         'code':  SOCIAL_EVENT_FARE_CODE,
         'description': u'ep2018 - Social Event'},
    ]

    assert sequence_equals(invoice_vat_10.invoice_items(),
                           expected_invoice_items_vat_10)

    assert sequence_equals(invoice_vat_20.invoice_items(),
                           expected_invoice_items_vat_20)

    # check numbers for vat 10%
    gross_price_vat_10 = ticket_price * ticket_amount

    net_price_vat_10 = normalize_price(gross_price_vat_10 / Decimal('1.1'))
    vat_value_vat_10 = gross_price_vat_10 - net_price_vat_10

    assert invoice_vat_10.price == gross_price_vat_10
    assert invoice_vat_10.net_price() == net_price_vat_10
    assert invoice_vat_10.vat_value() == vat_value_vat_10
    assert invoice_vat_10.html.startswith('<!DOCTYPE')
    assert len(invoice_vat_10.html) > 1000  # large html blob

    # check numbers for vat 20%
    gross_price_vat_20 = social_event_price * social_event_amount

    net_price_vat_20 = normalize_price(gross_price_vat_20 / Decimal('1.2'))
    vat_value_vat_20 = gross_price_vat_20 - net_price_vat_20

    assert invoice_vat_20.price == gross_price_vat_20
    assert invoice_vat_20.net_price() == net_price_vat_20
    assert invoice_vat_20.vat_value() == vat_value_vat_20
    assert invoice_vat_20.html.startswith('<!DOCTYPE')
    assert len(invoice_vat_20.html) > 1000  # large html blob

    # each OrderItem should have a corresponding Ticket
    assert Ticket.objects.all().count() == ticket_amount + social_event_amount

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


def create_order_and_invoice(assopy_user, fare, keep_as_placeholder=False):
    today = date.today()
    order = OrderFactory(user=assopy_user, items=[(fare, {'qty': 1})])

    with responses.RequestsMock() as rsps:
        # mocking responses for the invoice VAT exchange rate feature
        rsps.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
        fetch_and_store_latest_ecb_exrates()

    order.confirm_order(today)

    # confirm_order by default creates placeholders, but for most of the tests
    # we can upgrade them to proper invoices anyway.
    invoice = Invoice.objects.get(order=order)
    if keep_as_placeholder:
        return invoice
    return upgrade_invoice_placeholder_to_real_invoice(invoice)


@mark.django_db
def test_if_invoice_stores_information_about_the_seller(client):
    """
    Testing #591
    https://github.com/EuroPython/epcon/issues/591
    """

    # need this email to generate invoices/orders
    Email.objects.create(code='purchase-complete')
    fare = FareFactory()
    user = make_user()

    def invoice_url(invoice):
        return reverse("assopy-invoice-html", kwargs={
            'code': invoice.code,
            'order_code': invoice.order.code,
        })

    with freeze_time("2016-01-01"):
        # We need to log in again after every time travel, just in case.
        client.login(email='joedoe@example.com', password='password123')
        invoice = create_order_and_invoice(user.assopy_user, fare)
        assert invoice.code == "I/16.0001"
        assert invoice.emit_date == date(2016, 1, 1)
        assert invoice.issuer == ACPYSS_16
        assert invoice.html.startswith('<!DOCTYPE')

        response = client.get(invoice_url(invoice))
        assert ACPYSS_16 in response.content.decode('utf-8')

    with freeze_time("2017-01-01"):
        # We need to log in again after every time travel, just in case.
        client.login(email='joedoe@example.com', password='password123')
        invoice = create_order_and_invoice(user.assopy_user, fare)
        assert invoice.code == "I/17.0001"
        assert invoice.emit_date == date(2017, 1, 1)
        assert invoice.issuer == PYTHON_ITALIA_17
        assert invoice.html.startswith('<!DOCTYPE')

        response = client.get(invoice_url(invoice))
        assert PYTHON_ITALIA_17 in response.content.decode('utf-8')

    with freeze_time("2018-01-01"):
        # We need to log in again after every time travel, just in case.
        client.login(email='joedoe@example.com', password='password123')
        invoice = create_order_and_invoice(user.assopy_user, fare)

        assert invoice.code == "I/18.0001"
        assert invoice.emit_date == date(2018, 1, 1)
        assert invoice.issuer == EPS_18
        assert invoice.html.startswith('<!DOCTYPE')

        response = client.get(invoice_url(invoice))
        assert EPS_18 in response.content.decode('utf-8')


@mark.django_db
@responses.activate
def test_vat_in_GBP_for_2018(client):
    """
    https://github.com/EuroPython/epcon/issues/617
    """
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)

    Email.objects.create(code='purchase-complete')
    fare = FareFactory()
    user = make_user()

    with freeze_time("2018-05-05"):
        client.login(email='joedoe@example.com', password='password123')
        invoice = create_order_and_invoice(user.assopy_user, fare)
        assert invoice.html.startswith('<!DOCTYPE')
        assert invoice.vat_value()           == Decimal("1.67")
        assert invoice.vat_in_local_currency == Decimal("1.49")
        assert invoice.local_currency        == "GBP"
        assert invoice.exchange_rate         == Decimal('0.89165')
        assert invoice.exchange_rate_date    == EXAMPLE_ECB_DATE

        response = client.get(invoice.get_html_url())
        content = response.content.decode('utf-8')
        # The wording used to be different, so we had both checks in one line,
        # but beacuse of template change we had to separate them
        assert 'local-currency="GBP"' in content
        assert 'total-vat-in-local-currency="1.49"' in content

        # we're going to use whatever the date was received/cached from ECB XML
        # doesnt matter what emit date is
        assert "ECB rate used for VAT is 0.89165 GBP/EUR from 2018-03-06"\
            in content

        response = client.get(invoice.get_absolute_url())
        assert response['Content-Type'] == 'application/pdf'

    with freeze_time("2017-05-05"):
        client.login(email='joedoe@example.com', password='password123')
        invoice = create_order_and_invoice(user.assopy_user, fare)
        assert invoice.html.startswith('<!DOCTYPE')
        assert invoice.vat_value()           == Decimal("1.67")
        assert invoice.vat_in_local_currency == Decimal("1.67")
        assert invoice.local_currency        == "EUR"
        assert invoice.exchange_rate         == Decimal('1.0')
        assert invoice.exchange_rate_date    == date(2017, 5, 5)

        response = client.get(invoice.get_html_url())
        content = response.content.decode('utf-8')
        # not showing any VAT conversion because in 2017 we had just EUR
        assert "EUR"  in content
        assert "Total VAT is" not in content
        assert "ECB rate"  not in content

        response = client.get(invoice.get_absolute_url())
        assert response['Content-Type'] == 'application/pdf'


@mark.django_db
@responses.activate
@freeze_time("2018-05-05")
def test_create_invoice_with_many_items(client):
    """
    This test is meant to be used to test invoice template design.
    It creates a lot of different items on the invoice, and after that we can
    use serve(content) to easily check in the browser how the Invoice looks
    like.

    Freezing it at 2018 so we can easily check EP2018 invoices.
    """
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)

    Email.objects.create(code='purchase-complete')
    user = make_user()

    vat_rate_20, _ = Vat.objects.get_or_create(value=20)
    CONFERENCE = settings.CONFERENCE_CONFERENCE

    pre_create_typical_fares_for_conference(CONFERENCE, vat_rate_20)

    # Don't need to set dates for this test.
    # set_early_bird_fare_dates(CONFERENCE, yesterday, tomorrow)
    # set_regular_fare_dates(CONFERENCE, yesterday, tomorrow)
    random_fares = random.sample(Fare.objects.all(), 3)

    order = OrderFactory(user=user.assopy_user, items=[
        (fare, {'qty': i}) for i, fare in enumerate(random_fares, 1)
    ])
    with responses.RequestsMock() as rsps:
        # mocking responses for the invoice VAT exchange rate feature
        rsps.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
        fetch_and_store_latest_ecb_exrates()

    order.confirm_order(date.today())
    # invoice = Invoice.objects.get()
    # serve_response(PdfResponse(
    #     filename="some-invoice.pdf",
    #     content=render_invoice_as_html(invoice)
    # ))

    # testing debug panel
    # url = reverse("debugpanel_invoice_forcepreview",
    #               kwargs={'invoice_id': invoice.id})
    # url = reverse('debugpanel_invoice_placeholders')
    # client.login(email='joedoe@example.com', password='password123')
    # response = client.get(url)
    # serve_response(response)


@mark.django_db
@responses.activate
@freeze_time("2018-05-05")
def test_upgrade_invoices_for_2018_command(client):
    """
    """
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
    Email.objects.create(code='purchase-complete')
    fare = FareFactory()
    user = make_user()
    with freeze_time("2018-05-05"):
        client.login(email='joedoe@example.com', password='password123')
        invoice1 = create_order_and_invoice(
            user.assopy_user, fare, keep_as_placeholder=True
        )
        assert invoice1.html == VAT_NOT_AVAILABLE_PLACEHOLDER
        invoice2 = create_order_and_invoice(
            user.assopy_user, fare, keep_as_placeholder=True
        )
        assert invoice2.html == VAT_NOT_AVAILABLE_PLACEHOLDER
        assert invoice1.code != invoice2.code

    placeholders = Invoice.objects.filter(html=VAT_NOT_AVAILABLE_PLACEHOLDER)
    all_invoices = Invoice.objects.all()
    assert all_invoices.count() == 2
    assert placeholders.count() == 2

    call_command('upgrade_placeholder_invoices_for_2018')

    placeholders = Invoice.objects.filter(html=VAT_NOT_AVAILABLE_PLACEHOLDER)
    all_invoices = Invoice.objects.all()
    assert all_invoices.count() == 2
    assert placeholders.count() == 0


@mark.django_db
@responses.activate
def test_export_invoice_csv(client):
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
    Email.objects.create(code='purchase-complete')
    fare = FareFactory()
    user = make_user()

    client.login(email=user.email, password='password123')

    with freeze_time("2018-05-05"):
        invoice1 = create_order_and_invoice(
            user.assopy_user, fare, keep_as_placeholder=True
        )

    query_dict = QueryDict(mutable=True)
    query_dict['start_date'] = date(2018, 1, 1)
    query_dict['end_date'] = date.today()
    query_string = query_dict.urlencode()

    response = client.get(reverse('debugpanel_invoice_export_csv') + '?' + query_string)

    assert response.status_code == 200
    assert response['content-type'] == 'text/csv'

    invoice_reader = csv.reader(response.content.splitlines())
    invoice = next(invoice_reader)

    iter_column = iter(invoice)
    assert next(iter_column) == invoice1.code

    assert next(iter_column) == '2018-05-05'
    assert next(iter_column) == invoice1.order.user.user.get_full_name()

    next(iter_column)   # ignore the address
    assert next(iter_column) == invoice1.order.country.name
    assert next(iter_column) == invoice1.order.vat_number
    assert decimal.Decimal(next(iter_column)) == invoice1.net_price_in_local_currency
    assert decimal.Decimal(next(iter_column)) == invoice1.vat_in_local_currency
    assert decimal.Decimal(next(iter_column)) == invoice1.price_in_local_currency


@mark.django_db
@responses.activate
def test_export_invoice_csv_before_period(client):
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
    Email.objects.create(code='purchase-complete')
    fare = FareFactory()
    user = make_user()

    client.login(email=user.email, password='password123')

    with freeze_time("2018-04-05"):
        invoice1 = create_order_and_invoice(
            user.assopy_user, fare, keep_as_placeholder=True
        )

    query_dict = QueryDict(mutable=True)
    query_dict['start_date'] = date(2018, 5, 1)
    query_dict['end_date'] = date.today()
    query_string = query_dict.urlencode()

    response = client.get(reverse('debugpanel_invoice_export_csv') + '?' + query_string)

    assert response.status_code == 200
    assert response['content-type'] == 'text/csv'

    invoice_reader = csv.reader(response.content.splitlines())
    assert next(invoice_reader, None) is None


@mark.django_db
@responses.activate
def test_export_invoice(client):
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
    Email.objects.create(code='purchase-complete')
    fare = FareFactory()
    user = make_user()

    client.login(email=user.email, password='password123')

    with freeze_time('2018-05-05'):
        invoice1 = create_order_and_invoice(
            user.assopy_user, fare, keep_as_placeholder=True
        )

    query_dict = QueryDict(mutable=True)
    query_dict['start_date'] = date(2018, 1, 1)
    query_dict['end_date'] = date.today()
    query_string = query_dict.urlencode()

    response = client.get(reverse('debugpanel_invoice_export') + '?' + query_string)

    assert response.status_code == 200
    assert response['content-type'].startswith('text/html')

    assert '<tr id="invoice_{0}">'.format(invoice1.id) in response.content
