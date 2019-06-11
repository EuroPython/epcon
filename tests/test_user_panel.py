import pytest
import uuid
from datetime import date

from django.conf import settings
from django.utils import timezone
from django.core.urlresolvers import reverse

import responses
from django_factory_boy.auth import UserFactory

from assopy.models import Invoice, Order, OrderItem
from assopy.stripe.tests.factories import FareFactory, OrderFactory
from conference.models import Ticket, Conference, FARE_TICKET_TYPES
from conference.invoicing import create_invoices_for_order
from conference.tests.factories.fare import TicketFactory
from p3.models import TicketConference

from email_template.models import Email
from conference.currencies import (
    DAILY_ECB_URL,
    EXAMPLE_ECB_DAILY_XML,
    fetch_and_store_latest_ecb_exrates,
)

from tests.common_tools import make_user, setup_conference_with_typical_fares, create_valid_ticket_for_user_and_fare

pytestmark = [pytest.mark.django_db]


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


def create_order(assopy_user, fare):
    order = Order(
        uuid=str(uuid.uuid4()),
        user=assopy_user,
        code="O/#19.0001",
        order_type="student",
    )
    order.save()

    ticket = Ticket.objects.create(
        user=assopy_user.user, fare=fare, name=assopy_user.name()
    )
    OrderItem.objects.create(
        order=order,
        code=fare.code,
        ticket=ticket,
        description=f"{fare.description}",
        price=fare.price,
        vat=fare.vat_set.all()[0],
    )
    return order


@pytest.mark.xfail
def test_privacy_settings_requires_login():
    assert False


@pytest.mark.xfail
def test_privacy_settings_updates_profile():
    assert False


@responses.activate
def test_user_panel_manage_ticket(client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_NAME,
        conference_start="2019-07-08",
        conference_end="2019-07-14",
    )
    Email.objects.create(code="purchase-complete")
    fare = FareFactory()
    user = make_user(is_staff=True)

    client.login(email=user.email, password="password123")

    order = create_order(user.assopy_user, fare)
    order.payment_date = date.today()
    order.save()

    create_invoices_for_order(order)

    ticket1 = order.orderitem_set.get().ticket
    assert TicketConference.objects.all().count() == 0

    response = client.get(
        reverse("user_panel:manage_ticket", kwargs={"ticket_id": ticket1.id})
    )

    ticketconference = TicketConference.objects.get(ticket=ticket1)
    assert ticket1.name == ticketconference.name == user.assopy_user.name()


@responses.activate
def test_user_panel_update_ticket(client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_NAME,
        conference_start="2019-07-08",
        conference_end="2019-07-14",
    )
    Email.objects.create(code="purchase-complete")
    fare = FareFactory()
    user = make_user(is_staff=True)

    client.login(email=user.email, password="password123")

    invoice1 = create_order_and_invoice(user.assopy_user, fare)

    ticket1 = invoice1.order.orderitem_set.get().ticket
    ticketconference = TicketConference.objects.get(ticket=ticket1)

    assert ticket1.name == ticketconference.name
    newname = ticket1.name + " changed"

    response = client.post(
        reverse("user_panel:manage_ticket", kwargs={"ticket_id": ticket1.id}),
        {
            "name": newname,
            "diet": "other",
            "shirt_size": "xxxl",
            "tagline": "xyz",
            "days": "2019-07-10",
        },
    )

    ticket1.refresh_from_db()
    ticketconference.refresh_from_db()
    assert ticket1.name == newname
    assert ticketconference.name == newname
    assert ticketconference.diet == "other"
    assert ticketconference.shirt_size == "xxxl"
    assert ticketconference.tagline == "xyz"
    assert ticketconference.days == "2019-07-10"


def test_assigning_tickets_uses_case_insensitive_email_address(db, user_client):
    setup_conference_with_typical_fares()
    ticket = TicketFactory(user=user_client.user)
    target_email = 'MiXeDc4sE@test.tESt'
    target_user = UserFactory(email=target_email.lower())

    url = reverse('user_panel:assign_ticket', args=[ticket.id])
    payload = {'email': target_email}
    response = user_client.post(url, payload, follow=True)

    assert response.status_code == 200
    ticket.refresh_from_db()
    assert ticket.user == target_user


def test_assigning_ticket_to_inactive_user_displays_error(db, user_client):
    setup_conference_with_typical_fares()
    ticket = TicketFactory(user=user_client.user)
    target_user = UserFactory(is_active=False)
    target_email = target_user.email

    url = reverse('user_panel:assign_ticket', args=[ticket.id])
    payload = {'email': target_email}
    response = user_client.post(url, payload, follow=True)

    assert response.status_code == 200
    ticket.refresh_from_db()
    # The ticket has not been reassigned as the target user is inactive
    assert ticket.user != target_user
    assert ticket.user == user_client.user
    # A warning messages is displayed on the page
    assert "user does not exist" in response.content.decode()


<<<<<<< HEAD
def test_frozen_ticket_not_shown_in_dashboard(db, user_client):
    ticket = create_valid_ticket_for_user_and_fare(user=user_client.user)
    ticket.frozen = True
    ticket.save()

    url = reverse('user_panel:dashboard')
    response = user_client.get(url)

    assert response.status_code == 200
    # Link to assign ticket is displayed
    assert "assign ticket" not in response.content.decode().lower()
    assert reverse('user_panel:assign_ticket', args=[ticket.id]) not in response.content.decode().lower()
    assert "manage ticket" not in response.content.decode().lower()
    assert reverse('user_panel:manage_ticket', args=[ticket.id]) not in response.content.decode().lower()


def test_frozen_ticket_cannot_be_assigned(db, user_client):
    ticket = create_valid_ticket_for_user_and_fare(user=user_client.user)
    ticket.frozen = True
    ticket.save()

    url = reverse('user_panel:assign_ticket', args=[ticket.id])
    response = user_client.get(url)

    assert response.status_code == 403


def test_frozen_ticket_cannot_managed(db, user_client):
    ticket = create_valid_ticket_for_user_and_fare(user=user_client.user)
    ticket.frozen = True
    ticket.save()

    url = reverse('user_panel:manage_ticket', args=[ticket.id])
    response = user_client.get(url)

    assert response.status_code == 403


def test_other_fares_tickets_can_be_reassigned(db, user_client):
    setup_conference_with_typical_fares()
    ticket = TicketFactory(user=user_client.user, fare__ticket_type=FARE_TICKET_TYPES.other)
    target_user = UserFactory()
    target_email = target_user.email

    url = reverse('user_panel:assign_ticket', args=[ticket.id])
    payload = {'email': target_email}
    response = user_client.post(url, payload, follow=True)

    assert response.status_code == 200
    ticket.refresh_from_db()
    assert ticket.user == target_user


def test_other_fares_tickets_cannot_be_managed(db, user_client):
    setup_conference_with_typical_fares()
    ticket = TicketFactory(user=user_client.user, fare__ticket_type=FARE_TICKET_TYPES.other)
    target_user = UserFactory()
    target_email = target_user.email

    url = reverse('user_panel:manage_ticket', args=[ticket.id])
    payload = {'email': target_email}
    response = user_client.post(url, payload, follow=True)

    assert response.status_code == 403


@pytest.mark.xfail
def test_profile_settings_requires_login():
    assert False


@pytest.mark.xfail
def test_profile_settings_gets_initial_data():
    assert False


@pytest.mark.xfail
def test_profile_settings_updates_user_data():
    assert False


@pytest.mark.xfail
def test_profile_settings_forbids_using_registered_email():
    assert False


@pytest.mark.xfail
def test_profile_settings_updates_attendee_profile_data():
    assert False


@pytest.mark.xfail
def test_profile_settings_updates_p3_profile_data():
    assert False


@pytest.mark.xfail
def test_profile_settings_updates_image_settings():
    """
    4 scenarios to test - show no image, show gravatar, show url, show image.
    """
    assert False
