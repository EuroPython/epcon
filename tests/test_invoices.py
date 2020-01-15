import csv
import decimal
from datetime import date, datetime, timedelta
from decimal import Decimal
import random
import json

from django.http import QueryDict
from pytest import mark

from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils import timezone

from django_factory_boy import auth as auth_factories
from freezegun import freeze_time
import responses

from assopy.models import Country, Invoice, Order, Vat
from tests.factories import AssopyUserFactory, FareFactory, OrderFactory
from conference.models import AttendeeProfile, Ticket, Fare, Conference
from conference.invoicing import (
    ACPYSS_16,
    PYTHON_ITALIA_17,
    EPS_18,
    VAT_NOT_AVAILABLE_PLACEHOLDER,
    CSV_2018_REPORT_COLUMNS,
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
    serve_text,
)


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

    return Invoice.objects.create(
        code=invoice_code,
        order=order,
        emit_date=date.today(),
        price=Decimal(1337),
        vat=vat_10,
        html="<html>Here goes full html</html>",
        exchange_rate_date=date.today(),
    )


@mark.django_db
def test_invoice_html(client):
    # invoice_code must be validated via ASSOPY_IS_REAL_INVOICE
    invoice_code, order_code = "I123", "asdf"
    _prepare_invoice_for_basic_test(order_code, invoice_code)

    client.login(email="joedoe@example.com", password="password123")
    invoice_url = reverse(
        "assopy-invoice-html",
        kwargs={"order_code": order_code, "code": invoice_code},
    )
    response = client.get(invoice_url)

    assert (
        response.content.decode("utf-8") == "<html>Here goes full html</html>"
    )


@mark.django_db
def test_invoice_pdf(client):
    # invoice_code must be validated via ASSOPY_IS_REAL_INVOICE
    invoice_code, order_code = "I123", "asdf"
    _prepare_invoice_for_basic_test(order_code, invoice_code)

    client.login(email="joedoe@example.com", password="password123")
    invoice_url = reverse(
        "assopy-invoice-pdf",
        kwargs={"order_code": order_code, "code": invoice_code},
    )

    response = client.get(invoice_url)
    assert response.status_code == 200
    assert response["Content-type"] == "application/pdf"


@mark.django_db
def test_592_dont_display_invoices_for_years_before_2018(client):
    """
    https://github.com/EuroPython/epcon/issues/592

    Temporary(?) test for #592, until #591 is fixed.
    """

    # default password is 'password123' per django_factory_boy
    user = auth_factories.UserFactory(
        email="joedoe@example.com", is_active=True
    )

    # both are required to access user profile page.
    assopy_user = AssopyUserFactory(user=user)
    AttendeeProfile.objects.create(user=user, slug="foobar")

    client.login(email="joedoe@example.com", password="password123")

    # create some random Vat instance to the invoice creation works
    vat_10 = Vat.objects.create(value=10)

    # invoice_code must be validated via ASSOPY_IS_REAL_INVOICE
    invoice_code_2017, order_code_2017 = "I2017", "O2017"
    invoice_code_2018, order_code_2018 = "I2018", "O2018"

    order2017 = Order(user=assopy_user, code=order_code_2017)
    order2017.save()
    order2017.created = timezone.make_aware(datetime(2017, 12, 31))
    order2017.save()

    order2018 = Order(user=assopy_user, code=order_code_2018)
    order2018.save()
    order2018.created = timezone.make_aware(datetime(2018, 1, 1))
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

    assert invoice_code_2017 not in response.content.decode("utf-8")
    assert order_code_2017 not in response.content.decode("utf-8")

    assert invoice_code_2018 in response.content.decode("utf-8")
    assert order_code_2018 in response.content.decode("utf-8")

    assert reverse(
        "assopy-invoice-pdf",
        kwargs={"code": invoice_code_2018, "order_code": order_code_2018},
    ) in response.content.decode("utf-8")

    assert template_used(response, "assopy/profile.html")


def create_order_and_invoice(assopy_user, fare):
    order = OrderFactory(user=assopy_user, items=[(fare, {"qty": 1})])

    with responses.RequestsMock() as rsps:
        # mocking responses for the invoice VAT exchange rate feature
        rsps.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
        fetch_and_store_latest_ecb_exrates()

    order.confirm_order(timezone.now())

    # confirm_order by default creates placeholders, but for most of the tests
    # we can upgrade them to proper invoices anyway.
    invoice = Invoice.objects.get(order=order)
    return invoice


@mark.django_db
def test_if_invoice_stores_information_about_the_seller(client):
    """
    Testing #591
    https://github.com/EuroPython/epcon/issues/591
    """
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE, name=settings.CONFERENCE_NAME
    )

    # need this email to generate invoices/orders
    Email.objects.create(code="purchase-complete")
    fare = FareFactory()
    user = make_user()

    def invoice_url(invoice):
        return reverse(
            "assopy-invoice-html",
            kwargs={"code": invoice.code, "order_code": invoice.order.code},
        )

    with freeze_time("2016-01-01"):
        # We need to log in again after every time travel, just in case.
        client.login(email="joedoe@example.com", password="password123")
        invoice = create_order_and_invoice(user.assopy_user, fare)
        assert invoice.code == "I/16.0001"
        assert invoice.emit_date == date(2016, 1, 1)
        assert invoice.issuer == ACPYSS_16
        assert invoice.html.startswith("<!DOCTYPE")

        response = client.get(invoice_url(invoice))
        assert ACPYSS_16 in response.content.decode("utf-8")

    with freeze_time("2017-01-01"):
        # We need to log in again after every time travel, just in case.
        client.login(email="joedoe@example.com", password="password123")
        invoice = create_order_and_invoice(user.assopy_user, fare)
        assert invoice.code == "I/17.0001"
        assert invoice.emit_date == date(2017, 1, 1)
        assert invoice.issuer == PYTHON_ITALIA_17
        assert invoice.html.startswith("<!DOCTYPE")

        response = client.get(invoice_url(invoice))
        assert PYTHON_ITALIA_17 in response.content.decode("utf-8")

    with freeze_time("2018-01-01"):
        # We need to log in again after every time travel, just in case.
        client.login(email="joedoe@example.com", password="password123")
        invoice = create_order_and_invoice(user.assopy_user, fare)

        assert invoice.code == "I/18.0001"
        assert invoice.emit_date == date(2018, 1, 1)
        assert invoice.issuer == EPS_18
        assert invoice.html.startswith("<!DOCTYPE")

        response = client.get(invoice_url(invoice))
        assert EPS_18 in response.content.decode("utf-8")


@mark.django_db
@responses.activate
def test_vat_in_GBP_for_2018(client):
    """
    https://github.com/EuroPython/epcon/issues/617
    """
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)

    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE, name=settings.CONFERENCE_NAME
    )

    Email.objects.create(code="purchase-complete")
    fare = FareFactory()
    user = make_user()

    with freeze_time("2018-05-05"):
        client.login(email="joedoe@example.com", password="password123")
        invoice = create_order_and_invoice(user.assopy_user, fare)
        assert invoice.html.startswith("<!DOCTYPE")
        assert invoice.vat_value() == Decimal("1.67")
        assert invoice.vat_in_local_currency == Decimal("1.49")
        assert invoice.local_currency == "GBP"
        assert invoice.exchange_rate == Decimal("0.89165")
        assert invoice.exchange_rate_date == EXAMPLE_ECB_DATE

        response = client.get(invoice.get_html_url())
        content = response.content.decode("utf-8")
        # The wording used to be different, so we had both checks in one line,
        # but beacuse of template change we had to separate them
        assert 'local-currency="GBP"' in content
        assert 'total-vat-in-local-currency="1.49"' in content

        # we're going to use whatever the date was received/cached from ECB XML
        # doesnt matter what emit date is
        assert (
            "ECB rate used for VAT is 0.89165 GBP/EUR from 2018-03-06"
            in content
        )

        response = client.get(invoice.get_absolute_url())
        assert response["Content-Type"] == "application/pdf"

    with freeze_time("2017-05-05"):
        client.login(email="joedoe@example.com", password="password123")
        invoice = create_order_and_invoice(user.assopy_user, fare)
        assert invoice.html.startswith("<!DOCTYPE")
        assert invoice.vat_value() == Decimal("1.67")
        assert invoice.vat_in_local_currency == Decimal("1.67")
        assert invoice.local_currency == "EUR"
        assert invoice.exchange_rate == Decimal("1.0")
        assert invoice.exchange_rate_date == date(2017, 5, 5)

        response = client.get(invoice.get_html_url())
        content = response.content.decode("utf-8")
        # not showing any VAT conversion because in 2017 we had just EUR
        assert "EUR" in content
        assert "Total VAT is" not in content
        assert "ECB rate" not in content

        response = client.get(invoice.get_absolute_url())
        assert response["Content-Type"] == "application/pdf"


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

    Email.objects.create(code="purchase-complete")
    user = make_user()

    vat_rate_20, _ = Vat.objects.get_or_create(value=20)
    CONFERENCE = settings.CONFERENCE_CONFERENCE

    pre_create_typical_fares_for_conference(CONFERENCE, vat_rate_20)

    # Don't need to set dates for this test.
    # set_early_bird_fare_dates(CONFERENCE, yesterday, tomorrow)
    # set_regular_fare_dates(CONFERENCE, yesterday, tomorrow)
    random_fares = random.sample(list(Fare.objects.all()), 3)

    order = OrderFactory(
        user=user.assopy_user,
        items=[(fare, {"qty": i}) for i, fare in enumerate(random_fares, 1)],
    )
    with responses.RequestsMock() as rsps:
        # mocking responses for the invoice VAT exchange rate feature
        rsps.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
        fetch_and_store_latest_ecb_exrates()

    order.confirm_order(timezone.now())


@mark.django_db
@responses.activate
def test_export_invoice_csv(client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE, name=settings.CONFERENCE_NAME
    )
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
    Email.objects.create(code="purchase-complete")
    fare = FareFactory()
    user = make_user(is_staff=True)

    client.login(email=user.email, password="password123")

    with freeze_time("2018-05-05"):
        invoice1 = create_order_and_invoice(user.assopy_user, fare)

    query_dict = QueryDict(mutable=True)
    query_dict["start_date"] = date(2018, 1, 1)
    query_dict["end_date"] = date.today()
    query_string = query_dict.urlencode()

    response = client.get(
        reverse("debug_panel_invoice_export_for_tax_report_csv")
        + "?"
        + query_string
    )

    assert response.status_code == 200
    assert response["content-type"] == "text/csv"

    invoice_reader = csv.reader(response.content.decode("utf-8").splitlines())
    next(invoice_reader)  # skip header
    invoice = next(invoice_reader)

    iter_column = iter(invoice)
    assert next(iter_column) == invoice1.code

    assert next(iter_column) == "2018-05-05"
    assert next(iter_column) == invoice1.order.user.user.get_full_name()
    assert next(iter_column) == invoice1.order.card_name

    next(iter_column)  # ignore the address
    assert next(iter_column) == invoice1.order.country.name
    assert next(iter_column) == invoice1.order.vat_number
    next(iter_column)  # ignore the currency
    assert (
        decimal.Decimal(next(iter_column))
        == invoice1.net_price_in_local_currency
    )
    assert decimal.Decimal(next(iter_column)) == invoice1.vat_in_local_currency
    assert (
        decimal.Decimal(next(iter_column)) == invoice1.price_in_local_currency
    )


@mark.django_db
@responses.activate
def test_export_invoice_csv_before_period(client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE, name=settings.CONFERENCE_NAME
    )
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
    Email.objects.create(code="purchase-complete")
    fare = FareFactory()
    user = make_user(is_staff=True)

    client.login(email=user.email, password="password123")

    with freeze_time("2018-04-05"):
        create_order_and_invoice(user.assopy_user, fare)

    query_dict = QueryDict(mutable=True)
    query_dict["start_date"] = date(2018, 5, 1)
    query_dict["end_date"] = date.today()
    query_string = query_dict.urlencode()

    response = client.get(
        reverse("debug_panel_invoice_export_for_tax_report_csv")
        + "?"
        + query_string
    )

    assert response.status_code == 200
    assert response["content-type"] == "text/csv"

    invoice_reader = csv.reader(response.content.decode("utf-8").splitlines())
    header = next(invoice_reader)
    assert header == CSV_2018_REPORT_COLUMNS
    assert next(invoice_reader, None) is None


@mark.django_db
@responses.activate
def test_export_invoice(client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE, name=settings.CONFERENCE_NAME
    )
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
    Email.objects.create(code="purchase-complete")
    fare = FareFactory()
    user = make_user(is_staff=True)

    client.login(email=user.email, password="password123")

    with freeze_time("2018-05-05"):
        invoice1 = create_order_and_invoice(user.assopy_user, fare)

    query_dict = QueryDict(mutable=True)
    query_dict["start_date"] = date(2018, 1, 1)
    query_dict["end_date"] = date.today()
    query_string = query_dict.urlencode()

    response = client.get(
        reverse("debug_panel_invoice_export_for_tax_report")
        + "?"
        + query_string
    )

    assert response.status_code == 200
    assert response["content-type"].startswith("text/html")

    assert '<tr id="invoice_{0}">'.format(
        invoice1.id
    ) in response.content.decode("utf-8")


@mark.django_db
@responses.activate
def test_export_invoice_accounting_json(client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE, name=settings.CONFERENCE_NAME
    )
    responses.add(responses.GET, DAILY_ECB_URL, body=EXAMPLE_ECB_DAILY_XML)
    Email.objects.create(code="purchase-complete")
    fare = FareFactory()
    user = make_user(is_staff=True)

    client.login(email=user.email, password="password123")

    with freeze_time("2018-05-05"):
        invoice1 = create_order_and_invoice(user.assopy_user, fare)

    query_dict = QueryDict(mutable=True)
    query_dict["start_date"] = date(2018, 1, 1)
    query_dict["end_date"] = date.today()
    query_string = query_dict.urlencode()

    response = client.get(
        reverse("debug_panel_invoice_export_for_payment_reconciliation_json")
        + "?"
        + query_string
    )

    assert response.status_code == 200
    assert response["content-type"].startswith("application/json")

    data = json.loads(response.content)["invoices"]
    assert len(data) == 1
    assert data[0]["ID"] == invoice1.code
    assert decimal.Decimal(data[0]["net"]) == invoice1.net_price()
    assert decimal.Decimal(data[0]["vat"]) == invoice1.vat_value()
    assert decimal.Decimal(data[0]["gross"]) == invoice1.price
    assert data[0]["order"] == invoice1.order.code
    assert data[0]["stripe"] == invoice1.order.stripe_charge_id


def test_reissue_invoice(admin_client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE, name=settings.CONFERENCE_NAME
    )
    invoice_code, order_code = "I123", "asdf"
    invoice = _prepare_invoice_for_basic_test(order_code, invoice_code)

    NEW_CUSTOMER = "NEW CUSTOMER"
    assert Invoice.objects.all().count() == 1
    assert NEW_CUSTOMER not in Invoice.objects.latest("id").html

    url = reverse("debug_panel_reissue_invoice", args=[invoice.id])
    response = admin_client.get(url)
    assert response.status_code == 200

    response = admin_client.post(
        url, {"emit_date": "2018-01-01", "customer": NEW_CUSTOMER}
    )
    assert response.status_code == 302

    assert Invoice.objects.all().count() == 2
    assert NEW_CUSTOMER in Invoice.objects.latest("id").html
