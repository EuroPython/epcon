from datetime import timedelta
from decimal import Decimal
from unittest import mock
import uuid

from pytest import mark, raises, approx

from django.urls import reverse
from django.conf import settings
from django.contrib.messages import constants as messages_constants
from django.test import override_settings
from django.utils import timezone

from assopy.models import Order, ORDER_TYPE
from conference.cart import CartActions, ORDER_CONFIRMATION_EMAIL_SUBJECT
from conference.models import Ticket, Fare, FARE_TICKET_TYPES, StripePayment
from conference.fares import (
    set_early_bird_fare_dates,
    set_regular_fare_dates,
    set_other_fares_dates,
    SOCIAL_EVENT_FARE_CODE,
    SIM_CARD_FARE_CODE,
    ALL_POSSIBLE_FARE_CODES,
)
from p3.models import TicketConference
from tests.common_tools import (
    redirects_to,
    template_used,
    get_default_conference,
    setup_conference_with_typical_fares,
    contains_message,
    email_sent_with_subject,
)
from tests.factories import CouponFactory, CountryFactory, OrderFactory, VatFactory, FareFactory


@mark.parametrize(
    "url",
    [
        reverse("cart:step1_choose_type"),
        reverse("cart:step2_pick_tickets", args=["other"]),
        reverse("cart:step3_add_billing_info", args=["ABCDEFGH"]),
        reverse("cart:step4_payment", args=["ABCDEFGH"]),
    ],
)
def test_cart_requires_full_profile_data(db, user_client, url):
    user = user_client.user
    attendee_profile = user.attendeeprofile
    attendee_profile.gender = ""
    attendee_profile.save()
    attendee_profile.refresh_from_db()

    response = user_client.get(url)
    assert response.status_code == 302
    assert response.url == reverse("user_panel:profile_settings")


def test_first_step_of_cart_is_available_without_auth(db, client):
    url = reverse("cart:step1_choose_type")
    response = client.get(url)
    assert response.status_code == 200
    assert template_used(
        response, "ep19/bs/cart/step_1_choose_type_of_order.html"
    )


def test_first_step_has_links_to_second_step(db, client):
    url = reverse("cart:step1_choose_type")
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])
    second_step_personal = reverse(
        "cart:step2_pick_tickets", args=["personal"]
    )
    second_step_student = reverse("cart:step2_pick_tickets", args=["student"])

    response = client.get(url)

    assert second_step_company in response.content.decode()
    assert second_step_personal in response.content.decode()
    assert second_step_student in response.content.decode()


def test_other_fares_button_not_shown_when_other_fares_invalid(db, client):
    url = reverse("cart:step1_choose_type")
    second_step_other = reverse("cart:step2_pick_tickets", args=["other"])

    assert not Fare.objects.exclude(ticket_type=FARE_TICKET_TYPES.conference).exists()

    response = client.get(url)
    assert second_step_other not in response.content.decode()


def test_other_fares_button_shown_when_other_fares_valid(db, client):
    conference, _ = setup_conference_with_typical_fares()
    set_other_fares_dates(
        conference=conference,
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=7),
    )

    url = reverse("cart:step1_choose_type")
    second_step_other = reverse("cart:step2_pick_tickets", args=["other"])

    assert Fare.objects.exclude(ticket_type=FARE_TICKET_TYPES.conference).exists()

    response = client.get(url)
    assert second_step_other in response.content.decode()


def test_cart_second_step_requires_auth(db, client):
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])

    response = client.get(second_step_company)

    assert response.status_code == 302
    assert redirects_to(response, reverse('accounts:login'))


def test_second_step_doesnt_work_with_unkown_ticket_type(db, user_client):
    second_step_unkown = reverse("cart:step2_pick_tickets", args=["unkown"])

    with raises(AssertionError):
        user_client.get(second_step_unkown)


def test_cant_see_any_tickets_if_fares_are_not_available(db, user_client):
    setup_conference_with_typical_fares()
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])

    response = user_client.get(second_step_company)

    assert "No tickets available" in response.content.decode()


def test_cant_buy_any_tickets_if_fares_are_not_available(db, user_client):
    setup_conference_with_typical_fares()
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])

    response = user_client.post(
        second_step_company, {"TESP": 10, CartActions.buy_tickets: True},
        follow=True,
    )

    # Following the response to check if the message is correctly showed
    messages = list(response.context['messages'])
    assert len(messages) == 1
    assert messages[0].level == messages_constants.ERROR
    assert messages[0].message == "A selected fare is not available"
    assert Order.objects.all().count() == 0


@mark.parametrize(
    "ticket_category, expected_ticket_types",
    [
        ('personal', ['TRSP', 'TRLP', 'TRTP', 'TRCP', 'TRDP']),
        ('company', ['TRSC', 'TRLC', 'TRTC', 'TRCC', 'TRDC']),
        ('student', ['TRSS', 'TRLS', 'TRTS', 'TRCS', 'TRDS']),
        ('other', ['SIM1', 'VOUPE03']),
    ],
)
def test_cart_only_shows_correct_ticket_types(db, user_client, ticket_category, expected_ticket_types):
    setup_conference_with_typical_fares()
    set_regular_fare_dates(
        settings.CONFERENCE_CONFERENCE,
        timezone.now().date(),
        timezone.now().date() + timedelta(days=1),
    )
    set_other_fares_dates(
        settings.CONFERENCE_CONFERENCE,
        timezone.now().date(),
        timezone.now().date() + timedelta(days=1),
    )

    second_step_url = reverse("cart:step2_pick_tickets", args=[ticket_category])
    response = user_client.get(second_step_url)

    expected_tickets = Fare.objects.filter(code__in=expected_ticket_types).values('name')
    expected_names = [ticket['name'] for ticket in expected_tickets]
    for name in expected_names:
        assert name in response.content.decode()

    unexpected_tickets = Fare.objects.exclude(code__in=expected_ticket_types).values('name')
    unexpected_names = [ticket['name'] for ticket in unexpected_tickets]
    for name in unexpected_names:
        assert name not in response.content.decode()


def test_can_buy_tickets_if_fare_is_available(db, user_client):
    setup_conference_with_typical_fares()
    set_early_bird_fare_dates(
        settings.CONFERENCE_CONFERENCE,
        timezone.now().date(),
        timezone.now().date() + timedelta(days=1),
    )
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])

    response = user_client.post(
        second_step_company, {"TESP": 10, CartActions.buy_tickets: True}
    )

    assert response.status_code == 302
    order = Order.objects.get()
    assert redirects_to(
        response, reverse("cart:step3_add_billing_info", args=[order.uuid])
    )
    # Tickets are pre-created already even if we don't complete the order.
    assert Ticket.objects.all().count() == 10


def test_name_assigned_to_bought_tickets(db, user_client):
    setup_conference_with_typical_fares()
    set_early_bird_fare_dates(
        settings.CONFERENCE_CONFERENCE,
        timezone.now().date(),
        timezone.now().date() + timedelta(days=1),
    )
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])

    assert Ticket.objects.all().count() == 0
    assert TicketConference.objects.all().count() == 0

    response = user_client.post(
        second_step_company, {"TESP": 1, CartActions.buy_tickets: True}
    )

    assert response.status_code == 302
    order = Order.objects.get()
    assert redirects_to(
        response, reverse("cart:step3_add_billing_info", args=[order.uuid])
    )
    # Tickets are pre-created already even if we don't complete the order.
    assert Ticket.objects.all().count() == 1
    ticket = Ticket.objects.get()

    assert ticket.name == order.user.name()


def test_can_buy_training_tickets(db, user_client):
    setup_conference_with_typical_fares()
    set_regular_fare_dates(
        settings.CONFERENCE_CONFERENCE,
        timezone.now().date(),
        timezone.now().date() + timedelta(days=1),
    )
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])

    response = user_client.post(
        second_step_company, {"TRTC": 10, CartActions.buy_tickets: True}
    )

    assert response.status_code == 302
    order = Order.objects.get()
    assert redirects_to(
        response, reverse("cart:step3_add_billing_info", args=[order.uuid])
    )
    # Tickets are pre-created already even if we don't complete the order.
    assert Ticket.objects.all().count() == 10


def test_can_buy_combined_tickets(db, user_client):
    setup_conference_with_typical_fares()
    set_regular_fare_dates(
        settings.CONFERENCE_CONFERENCE,
        timezone.now().date(),
        timezone.now().date() + timedelta(days=1),
    )
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])

    response = user_client.post(
        second_step_company, {"TRCC": 10, CartActions.buy_tickets: True}
    )

    assert response.status_code == 302
    order = Order.objects.get()
    assert redirects_to(
        response, reverse("cart:step3_add_billing_info", args=[order.uuid])
    )
    # Tickets are pre-created already even if we don't complete the order.
    assert Ticket.objects.all().count() == 10


def test_can_buy_other_fares(db, user_client):
    setup_conference_with_typical_fares()
    set_other_fares_dates(
        settings.CONFERENCE_CONFERENCE,
        timezone.now().date(),
        timezone.now().date() + timedelta(days=1),
    )
    second_step_other = reverse("cart:step2_pick_tickets", args=["other"])

    response = user_client.post(
        second_step_other,
        {
            SIM_CARD_FARE_CODE: 1,
            SOCIAL_EVENT_FARE_CODE: 1,
            CartActions.buy_tickets: True,
        }
    )

    assert response.status_code == 302
    order = Order.objects.get()
    assert redirects_to(
        response, reverse("cart:step3_add_billing_info", args=[order.uuid])
    )

    assert Ticket.objects.all().count() == 2


def test_step2_no_fares_selected(db, user_client):
    setup_conference_with_typical_fares()
    set_regular_fare_dates(
        settings.CONFERENCE_CONFERENCE,
        timezone.now().date(),
        timezone.now().date() + timedelta(days=1),
    )
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])

    response = user_client.post(
        second_step_company, data={CartActions.buy_tickets: True}, follow=True,
    )

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/cart/step_2_pick_tickets.html")
    assert contains_message(response, 'Please select some tickets')


def test_step2_invalid_fare_code_for_fares_outside_of_validity_window(db, user_client):
    setup_conference_with_typical_fares()
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])

    response = user_client.post(
        second_step_company, {"TRCC": 1, CartActions.buy_tickets: True}, follow=True,
    )

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/cart/step_2_pick_tickets.html")
    assert contains_message(response, 'A selected fare is not available')


def test_step2_apply_discount_with_invalid_coupon(db, user_client):
    setup_conference_with_typical_fares()
    set_regular_fare_dates(
        settings.CONFERENCE_CONFERENCE,
        timezone.now().date(),
        timezone.now().date() + timedelta(days=1),
    )
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])

    response = user_client.post(
        second_step_company, data=
        {
            "TRCC": 1,
            CartActions.apply_discount_code: True,
            'discount_code': 'fake code',
        }, follow=True,
    )

    assert response.status_code == 200
    assert template_used(
        response, "ep19/bs/cart/step_2_pick_tickets.html"
    )
    assert contains_message(response, 'The discount code provided expired or is invalid')


def test_cart_computes_discounts_correctly(db, user_client):
    setup_conference_with_typical_fares()
    set_early_bird_fare_dates(
        settings.CONFERENCE_CONFERENCE,
        timezone.now().date(),
        timezone.now().date() + timedelta(days=1),
    )
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])
    percent_discount = 25
    coupon = CouponFactory(user=user_client.user.assopy_user, value=f'{percent_discount}%')
    coupon_fare = coupon.fares.first()
    order_ticket_count = 3

    response = user_client.post(
        second_step_company,
        {
            coupon_fare.code: order_ticket_count,
            CartActions.apply_discount_code: True,
            'discount_code': coupon.code,
        }
    )

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/cart/step_2_pick_tickets.html")

    # No order or tickets should be created
    assert not Order.objects.all().exists()
    assert not Ticket.objects.all().exists()
    # The calculated discount should exist in the context
    calculation = response.context['calculation']
    assert calculation.full_price == order_ticket_count * coupon_fare.price
    assert (calculation.total_discount
            == (order_ticket_count * coupon_fare.price) * Decimal(percent_discount / 100))
    assert (calculation.final_price
            == (order_ticket_count * coupon_fare.price) * Decimal((100 - percent_discount) / 100))


@mark.xfail
def test_manage_and_assign_ticket_urls_not_shown_in_step_3(db):
    assert False


@mark.xfail
def test_manage_and_assign_ticket_urls_not_shown_in_step_4(db):
    assert False


@mark.xfail
def test_cart_only_allows_to_buy_less_than_max_number_of_tickets(db):
    # TODO: This is now only enforced on the frontend - the backend implementation is missing
    assert False


def test_can_apply_personal_ticket_coupon(db, user_client):
    setup_conference_with_typical_fares()
    set_early_bird_fare_dates(
        settings.CONFERENCE_CONFERENCE,
        timezone.now().date(),
        timezone.now().date() + timedelta(days=1),
    )
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])
    percent_discount = 25
    coupon = CouponFactory(user=user_client.user.assopy_user, value=f'{percent_discount}%')
    coupon_fare = coupon.fares.first()
    order_ticket_count = 10

    response = user_client.post(
        second_step_company,
        {
            coupon_fare.code: order_ticket_count,
            CartActions.buy_tickets: True,
            'discount_code': coupon.code,
        }
    )

    assert response.status_code == 302
    order = Order.objects.get()
    assert redirects_to(
        response, reverse("cart:step3_add_billing_info", args=[order.uuid])
    )

    # Tickets are pre-created already even if we don't complete the order.
    assert Ticket.objects.all().count() == order_ticket_count
    # Order includes the coupon item with the coupon code
    assert order.orderitem_set.count() == order_ticket_count + 1
    assert order.orderitem_set.filter(code=coupon.code).exists()
    # Check the discount is applied correctly
    assert order.total() == (
        order_ticket_count * coupon_fare.price * Decimal((100 - percent_discount) / 100)
    )


def test_cannot_apply_coupon_if_fare_mismatch(db, user_client):
    setup_conference_with_typical_fares()
    set_early_bird_fare_dates(
        settings.CONFERENCE_CONFERENCE,
        timezone.now().date(),
        timezone.now().date() + timedelta(days=1),
    )
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])
    coupon_fare = Fare.objects.get(code='TESS')
    coupon = CouponFactory(
        user=user_client.user.assopy_user,
        fares=[coupon_fare],
    )
    assert coupon.start_validity
    assert coupon.end_validity

    order_ticket_count = 1
    response = user_client.post(
        second_step_company,
        {"TESP": order_ticket_count, CartActions.buy_tickets: True, 'discount_code': coupon.code}
    )
    assert response.status_code == 302
    order = Order.objects.get()
    assert redirects_to(
        response, reverse("cart:step3_add_billing_info", args=[order.uuid])
    )

    # No discount is applied when purchasing fares not covered by coupons.
    assert order.total() == order_ticket_count * coupon_fare.price
    # Tickets are pre-created already even if we don't complete the order.
    assert Ticket.objects.all().count() == order_ticket_count
    # Order does not include the coupon item with the coupon code
    assert order.orderitem_set.count() == order_ticket_count
    assert not order.orderitem_set.filter(code=coupon.code).exists()


def test_can_apply_coupon_with_null_dates(db, user_client):
    setup_conference_with_typical_fares()
    set_early_bird_fare_dates(
        settings.CONFERENCE_CONFERENCE,
        timezone.now().date(),
        timezone.now().date() + timedelta(days=1),
    )
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])
    coupon_fare = Fare.objects.get(code='TESS')
    coupon = CouponFactory(
        user=user_client.user.assopy_user,
        fares=[coupon_fare],
        start_validity=None,
        end_validity=None,
    )
    order_ticket_count = 1

    response = user_client.post(
        second_step_company,
        {
            coupon_fare.code: order_ticket_count,
            CartActions.buy_tickets: True,
            'discount_code': coupon.code,
        }
    )

    assert response.status_code == 302
    order = Order.objects.get()
    assert redirects_to(
        response, reverse("cart:step3_add_billing_info", args=[order.uuid])
    )

    # Discount successfully applied
    assert order.total() < order_ticket_count * coupon_fare.price
    # Tickets are pre-created already even if we don't complete the order.
    assert Ticket.objects.all().count() == order_ticket_count
    # Order includes the coupon item with the coupon code
    assert order.orderitem_set.count() == order_ticket_count + 1
    assert order.orderitem_set.filter(code=coupon.code).exists()


def test_cart_third_step_requires_auth(db, client):
    _, fares = setup_conference_with_typical_fares()
    order = OrderFactory(items=[(fares[0], {"qty": 1})])

    billing_step_url = reverse("cart:step3_add_billing_info", args=[order.uuid])
    response = client.get(billing_step_url)

    assert response.status_code == 302
    assert redirects_to(response, reverse('accounts:login'))


def test_user_can_add_non_company_billing_info(db, user_client):
    _, fares = setup_conference_with_typical_fares()
    order = OrderFactory(items=[(fares[0], {"qty": 1})], order_type=ORDER_TYPE.personal)
    payload = dict(
        card_name='John Doe',
        country=CountryFactory().iso,
        address='Calle Street 11',
        # The following fields are only available for business orders so should
        # be ignored by the view.
        billing_notes='Some notes',
        vat_number='ES123245678',
    )

    billing_step_url = reverse("cart:step3_add_billing_info", args=[order.uuid])
    response = user_client.post(billing_step_url, data=payload)

    assert redirects_to(
        response, reverse("cart:step4_payment", args=[order.uuid])
    )

    order.refresh_from_db()
    assert order.card_name == payload['card_name']
    assert order.country.iso == payload['country']
    assert order.address == payload['address']
    assert order.billing_notes == ''
    assert order.vat_number == ''


def test_user_can_add_company_billing_info(db, user_client):
    _, fares = setup_conference_with_typical_fares()
    order = OrderFactory(items=[(fares[0], {"qty": 1})], order_type=ORDER_TYPE.company)
    payload = dict(
        card_name='John Doe',
        country=CountryFactory().iso,
        address='Calle Street 11',
        billing_notes='Some notes',
        vat_number='ES123245678',
    )

    billing_step_url = reverse("cart:step3_add_billing_info", args=[order.uuid])
    response = user_client.post(billing_step_url, data=payload)

    assert redirects_to(
        response, reverse("cart:step4_payment", args=[order.uuid])
    )

    order.refresh_from_db()
    assert order.card_name == payload['card_name']
    assert order.country.iso == payload['country']
    assert order.address == payload['address']
    assert order.billing_notes == payload['billing_notes']
    assert order.vat_number == payload['vat_number']


def test_user_cant_see_tickets_for_non_completed_orders(db, user_client):
    _, fares = setup_conference_with_typical_fares()
    order_fare = fares[0]
    order = OrderFactory(
        user=user_client.user.assopy_user,
        items=[(order_fare, {"qty": 1})],
    )
    assert not order._complete

    user_panel_url = reverse('user_panel:dashboard')
    response = user_client.get(user_panel_url)

    assert response.status_code == 200
    assert order_fare.code not in response.content.decode()


def test_user_cant_assign_tickets_for_non_completed_orders(db, user_client):
    _, fares = setup_conference_with_typical_fares()
    order_fare = fares[0]
    order = OrderFactory(
        user=user_client.user.assopy_user,
        items=[(order_fare, {"qty": 1})],
    )
    assert not order._complete
    assert order.orderitem_set.count() == 1
    ticket = order.orderitem_set.first().ticket

    user_panel_url = reverse('user_panel:manage_ticket', args=[ticket.id])
    response = user_client.get(user_panel_url)

    assert response.status_code == 403


def test_user_cant_manage_tickets_for_non_completed_orders(db, user_client):
    _, fares = setup_conference_with_typical_fares()
    order_fare = fares[0]
    order = OrderFactory(
        user=user_client.user.assopy_user,
        items=[(order_fare, {"qty": 1})],
    )
    assert not order._complete
    assert order.orderitem_set.count() == 1
    ticket = order.orderitem_set.first().ticket

    user_panel_url = reverse('user_panel:assign_ticket', args=[ticket.id])
    response = user_client.get(user_panel_url)

    assert response.status_code == 403


def test_cart_fourth_step_requires_auth(db, client):
    _, fares = setup_conference_with_typical_fares()
    order = OrderFactory(items=[(fares[0], {"qty": 1})])

    payment_step_url = reverse("cart:step4_payment", args=[order.uuid])
    response = client.get(payment_step_url)

    assert redirects_to(response, reverse('accounts:login'))


@override_settings(STRIPE_PUBLISHABLE_KEY='pk_fake')
def test_cart_fourth_step_renders_correctly(db, user_client):
    _, fares = setup_conference_with_typical_fares()
    order = OrderFactory(items=[(fares[0], {"qty": 1})])

    payment_step_url = reverse("cart:step4_payment", args=[order.uuid])
    response = user_client.get(payment_step_url)

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/cart/step_4_payment.html")


def test_cart_payment_with_zero_total(db, user_client):
    _, fares = setup_conference_with_typical_fares()
    coupon = CouponFactory(user=user_client.user.assopy_user, value='100%')
    order = OrderFactory(user=user_client.user.assopy_user, items=[(fares[0], {"qty": 1})], coupons=[coupon])

    payment_step_url = reverse("cart:step4_payment", args=[order.uuid])
    response = user_client.post(payment_step_url)

    order_complete_url = reverse("cart:step5_congrats_order_complete", args=[order.uuid])
    assert redirects_to(response, order_complete_url)

    order.refresh_from_db()
    assert order.payment_date
    assert order.payment_date.date() == timezone.now().date()
    assert order.invoices.count() == 1
    assert email_sent_with_subject(ORDER_CONFIRMATION_EMAIL_SUBJECT)


@mock.patch('conference.cart.prepare_for_payment')
@mock.patch('conference.cart.verify_payment')
def test_cart_payment_with_non_zero_total(mock_prepare_for_payment, mock_verify_payment, db, user_client):
    _, fares = setup_conference_with_typical_fares()
    order = OrderFactory(items=[(fares[0], {"qty": 1})])
    payment = StripePayment.objects.create(
        amount=fares[0].price,
        order=order,
        user=user_client.user,
        uuid=str(uuid.uuid4()),
    )

    mock_prepare_for_payment.return_value = payment

    payment_step_url = reverse("cart:step4_payment", args=[order.uuid])
    response = user_client.get(payment_step_url)

    verify_payment_url = reverse("cart:step4b_verify_payment", args=(order.stripepayment_set.all()[0].uuid,
                                                                     'SESSION_ID'))
    response = user_client.get(verify_payment_url)
    order_complete_url = reverse("cart:step5_congrats_order_complete", args=[order.uuid])
    assert redirects_to(response, order_complete_url)

    order.refresh_from_db()
    assert order.payment_date
    assert order.payment_date.date() == timezone.now().date()
    assert order.invoices.count() == 1
    assert StripePayment.objects.count() == 1
    assert mock_prepare_for_payment.call_count == 1
    assert mock_verify_payment.call_count == 1
    assert email_sent_with_subject(ORDER_CONFIRMATION_EMAIL_SUBJECT)


def test_cart_fifth_step_requires_auth(db, client):
    _, fares = setup_conference_with_typical_fares()
    order = OrderFactory(items=[(fares[0], {"qty": 1})])

    order_complete_url = reverse("cart:step5_congrats_order_complete", args=[order.uuid])
    response = client.get(order_complete_url)

    assert response.status_code == 302
    assert redirects_to(response, reverse('accounts:login'))


def test_cart_fifth_step_renders_correctly(db, user_client):
    _, fares = setup_conference_with_typical_fares()
    order = OrderFactory(items=[(fares[0], {"qty": 1})])

    order_complete_url = reverse("cart:step5_congrats_order_complete", args=[order.uuid])
    response = user_client.get(order_complete_url)

    assert response.status_code == 200
    assert template_used(
        response, "ep19/bs/cart/step_5_congrats_order_complete.html"
    )


def test_order_aggregate_vat_rounding_with_discount(db):
    get_default_conference()
    vat = VatFactory(value=20)

    valid_fare_codes = list(ALL_POSSIBLE_FARE_CODES.keys())
    fare_one = FareFactory(price=25, vat_set=[vat], code=valid_fare_codes[0])
    fare_two = FareFactory(price=13, vat_set=[vat], code=valid_fare_codes[1])
    fare_three = FareFactory(price=-38, vat_set=[vat], code=valid_fare_codes[2])

    order = OrderFactory(
        items=[(fare_one, {"qty": 1}), (fare_two, {"qty": 1}), (fare_three, {"qty": 1})]
    )

    assert order.total() == 0
    assert order.total_vat_amount() == 0


def test_order_aggregate_vat_rounding(db):
    get_default_conference()
    vat = VatFactory(value=Decimal(20))
    fare = FareFactory(price=100, vat_set=[vat])

    order = OrderFactory(items=[(fare, {"qty": 1})])

    assert order.total_vat_amount() < order.total()
    # The `total_vat_amount` calculation is rounded to two decimal points, while the
    # manual calculation isn't - hence the need for approximate comparison
    assert order.total_vat_amount() == approx(
        (order.total() * vat.value / 100) / (1 + vat.value / 100), abs=0.01
    )
