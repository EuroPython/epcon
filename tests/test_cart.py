from datetime import date, timedelta

from pytest import mark, raises
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.messages import constants as messages_constants
from tests.common_tools import redirects_to, template_used
from assopy.models import Order
from conference.models import Conference, Ticket
from conference.fares import (
    pre_create_typical_fares_for_conference,
    set_early_bird_fare_dates,
)
from assopy.models import Vat
from conference.cart import CartActions

DEFAULT_VAT_RATE = "20"  # 20%


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


def test_cart_second_step_requires_auth(db, client):
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])

    response = client.get(second_step_company)

    assert response.status_code == 302
    assert redirects_to(response, "/accounts/login/")


def test_second_step_doesnt_work_with_unkown_ticket_type(db, ep_admin_client):
    # NOTE: this is using admin_client because of @staff_member_required in the
    # testing period. Later the fixture should be changed back to user_client
    second_step_unkown = reverse("cart:step2_pick_tickets", args=["unkown"])

    with raises(AssertionError):
        ep_admin_client.get(second_step_unkown)


def test_cant_see_any_tickets_if_fares_are_not_available(db, ep_admin_client):
    # NOTE: this is using admin_client because of @staff_member_required in the
    # testing period. Later the fixture should be changed back to user_client
    _setup()
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])

    response = ep_admin_client.get(second_step_company)

    assert "No tickets available" in response.content.decode()


def test_cant_buy_any_tickets_if_fares_are_not_available(db, ep_admin_client):
    # NOTE: this is using admin_client because of @staff_member_required in the
    # testing period. Later the fixture should be changed back to user_client
    _setup()
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])

    response = ep_admin_client.post(
        second_step_company, {"TESP": 10, CartActions.buy_tickets: True},
        follow=True,
    )

    # Following the response to check if the message is correctly showed
    messages = list(response.context['messages'])
    assert len(messages) == 1
    assert messages[0].level == messages_constants.ERROR
    assert messages[0].message == "A selected fare is not available"
    assert Order.objects.all().count() == 0


def test_can_buy_tickets_if_fare_is_available(db, ep_admin_client):
    # NOTE: this is using admin_client because of @staff_member_required in the
    # testing period. Later the fixture should be changed back to user_client
    _setup()
    set_early_bird_fare_dates(
        settings.CONFERENCE_CONFERENCE,
        date.today(),
        date.today() + timedelta(days=1),
    )
    second_step_company = reverse("cart:step2_pick_tickets", args=["company"])

    response = ep_admin_client.post(
        second_step_company, {"TESP": 10, CartActions.buy_tickets: True}
    )

    assert response.status_code == 302
    order = Order.objects.get()
    assert redirects_to(
        response, reverse("cart:step3_add_billing_info", args=[order.uuid])
    )
    # Tickets are pre-created already even if we don't complete the order.
    assert Ticket.objects.all().count() == 10


def test_user_can_add_billing_info(db, ep_admin_client):
    # NOTE: this is using admin_client because of @staff_member_required in the
    # testing period. Later the fixture should be changed back to user_client
    _setup()
    ...


def test_user_cant_see_or_assign_tickets_for_non_completed_orders(
    db, ep_admin_client
):
    # NOTE: this is using admin_client because of @staff_member_required in the
    # testing period. Later the fixture should be changed back to user_client
    ...


def _setup(start=date(2019, 7, 8), end=date(2019, 7, 14)):
    Conference.objects.get_or_create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_NAME,
        # using 2018 dates
        # those dates are required for Tickets to work.
        # (for setting up/rendering attendance days)
        conference_start=start,
        conference_end=end,
    )
    default_vat_rate, _ = Vat.objects.get_or_create(value=DEFAULT_VAT_RATE)
    pre_create_typical_fares_for_conference(
        settings.CONFERENCE_CONFERENCE,
        default_vat_rate
    )


def test_third_step_redirects_to_step_four(db):
    ...


def test_fourth_step_redirects_to_step_five(db):
    ...


def test_cart_third_step_requires_auth(db):
    ...


def test_cart_fourth_step(db):
    ...


def test_cart_only_shows_correct_ticket_types(db):
    # Parametrise with ticket type
    ...


def test_cart_only_allows_to_buy_less_than_max_number_of_tickets(db):
    ...


def test_cart_computes_discounts_correctly(db):
    ...


def test_cart_applies_discounts_correctly(db):
    ...


@mark.parametrize(
    "url",
    [
        reverse("cfp:step1_submit_proposal"),
        # using some random uuid because we just need to resolve url
        reverse("cfp:step2_add_speakers", args=["ABCDEFI"]),
        reverse("cfp:step3_thanks", args=["ABCDEFI"]),
    ],
)
def test_if_cfp_pages_are_login_required(db, client, url):
    response = client.get(url)

    assert response.status_code == 302
    assert redirects_to(response, "/accounts/login/")
