import pytest
import uuid

from django.conf import settings
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

import responses

from assopy.models import Invoice, Order, OrderItem
from conference.models import Ticket, FARE_TICKET_TYPES
from conference.invoicing import create_invoices_for_order
from conference.user_panel import PICTURE_CHOICES
from p3.models import TicketConference

from email_template.models import Email
from conference.currencies import (
    DAILY_ECB_URL,
    EXAMPLE_ECB_DAILY_XML,
    fetch_and_store_latest_ecb_exrates,
)

from .common_tools import (
    make_user,
    create_valid_ticket_for_user_and_fare,
    get_default_conference,
    redirects_to,
    template_used,
)
from . import factories

pytestmark = [pytest.mark.django_db]


def create_order_and_invoice(assopy_user, fare):
    order = factories.OrderFactory(user=assopy_user, items=[(fare, {"qty": 1})])

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


def test_privacy_settings_requires_login(client):
    url = reverse('user_panel:privacy_settings')

    response = client.get(url)

    assert redirects_to(response, reverse("accounts:login"))


def test_privacy_settings_updates_profile(user_client):
    url = reverse('user_panel:privacy_settings')
    profile = user_client.user.attendeeprofile.p3_profile
    assert profile.spam_recruiting is False
    assert profile.spam_sms is False
    assert profile.spam_user_message is False

    response = user_client.post(url, data=dict(
        spam_recruiting=True,
        spam_sms=True,
        spam_user_message=True,
    ))

    assert response.status_code == 200
    profile.refresh_from_db()
    assert profile.spam_recruiting is True
    assert profile.spam_sms is True
    assert profile.spam_user_message is True


@responses.activate
def test_user_panel_manage_ticket(client):
    get_default_conference()
    Email.objects.create(code="purchase-complete")
    fare = factories.FareFactory()
    user = make_user(is_staff=True)

    client.login(email=user.email, password="password123")

    order = create_order(user.assopy_user, fare)
    order.payment_date = timezone.now()
    order.save()

    create_invoices_for_order(order)

    ticket1 = order.orderitem_set.get().ticket
    assert TicketConference.objects.all().count() == 0

    response = client.get(
        reverse("user_panel:manage_ticket", kwargs={"ticket_id": ticket1.id})
    )
    assert response.status_code == 200

    ticketconference = TicketConference.objects.get(ticket=ticket1)
    assert ticket1.name == ticketconference.name == user.assopy_user.name()


@responses.activate
def test_user_panel_update_ticket(client):
    get_default_conference()
    Email.objects.create(code="purchase-complete")
    fare = factories.FareFactory()
    user = make_user(is_staff=True)

    client.login(email=user.email, password="password123")

    invoice1 = create_order_and_invoice(user.assopy_user, fare)

    ticket1 = invoice1.order.orderitem_set.get().ticket
    ticketconference = TicketConference.objects.get(ticket=ticket1)

    response = client.post(
        reverse("user_panel:manage_ticket", kwargs={"ticket_id": ticket1.id}),
        {
            "diet": "other",
            "shirt_size": "xxxl",
            "tagline": "xyz",
            "days": "2019-07-10",
        },
    )
    assert response.status_code == 302

    ticket1.refresh_from_db()
    ticketconference.refresh_from_db()
    assert ticket1.name == ticketconference.name
    assert ticketconference.diet == "other"
    assert ticketconference.shirt_size == "xxxl"
    assert ticketconference.tagline == "xyz"
    assert ticketconference.days == "2019-07-10"


@responses.activate
def test_user_panel_update_ticket_cannot_update_name(client):
    get_default_conference()
    Email.objects.create(code="purchase-complete")
    fare = factories.FareFactory()
    user = make_user(is_staff=True)

    client.login(email=user.email, password="password123")

    invoice1 = create_order_and_invoice(user.assopy_user, fare)
    ticket1 = invoice1.order.orderitem_set.get().ticket
    ticketconference = TicketConference.objects.get(ticket=ticket1)

    assert ticket1.name == ticketconference.name
    old_name = ticket1.name
    new_name = ticket1.name + " changed"

    response = client.post(
        reverse("user_panel:manage_ticket", kwargs={"ticket_id": ticket1.id}),
        {
            "name": new_name
        },
    )
    assert response.status_code == 200

    ticket1.refresh_from_db()
    ticketconference.refresh_from_db()
    assert ticket1.name == old_name
    assert ticketconference.name == old_name


def test_ticket_buyer_is_shown_assign_ticket_link(user_client):
    ticket = create_valid_ticket_for_user_and_fare(user=user_client.user)

    url = reverse('user_panel:dashboard')
    response = user_client.get(url)

    assert response.status_code == 200
    # Link to assign ticket is displayed
    assert "assign ticket" in response.content.decode().lower()
    assert reverse('user_panel:assign_ticket', args=[ticket.id]) in response.content.decode().lower()


def test_ticket_buyer_can_assign_ticket(user_client):
    ticket = create_valid_ticket_for_user_and_fare(user=user_client.user)
    assignee = factories.UserFactory()

    url = reverse('user_panel:assign_ticket', args=[ticket.id])
    payload = {'email': assignee.email}
    response = user_client.post(url, data=payload, follow=True)

    assert response.status_code == 200

    # Ticket successfully reassigned
    ticket.refresh_from_db()
    assert ticket.user == assignee


def test_ticket_assignee_is_not_shown_assign_ticket_link(user_client):
    buyer = factories.UserFactory()
    ticket = create_valid_ticket_for_user_and_fare(user=buyer)
    ticket.user = user_client.user

    url = reverse('user_panel:dashboard')
    response = user_client.get(url)

    assert response.status_code == 200
    # Link to assign ticket is not displayed since the user is not the ticket buyer
    assert "assign ticket" not in response.content.decode().lower()
    assert reverse('user_panel:assign_ticket', args=[ticket.id]) not in response.content.decode().lower()


def test_ticket_assignee_cannot_reassign_ticket(user_client):
    buyer = factories.UserFactory()
    ticket = create_valid_ticket_for_user_and_fare(user=buyer)
    ticket.user = user_client.user

    url = reverse('user_panel:assign_ticket', args=[ticket.id])
    payload = {'email': buyer.email}
    response = user_client.post(url, data=payload, follow=True)

    assert response.status_code == 403


def test_assigning_tickets_uses_case_insensitive_email_address(user_client):
    ticket = create_valid_ticket_for_user_and_fare(user=user_client.user)
    target_email = 'MiXeDc4sE@test.tESt'
    target_user = factories.UserFactory(email=target_email.lower())

    url = reverse('user_panel:assign_ticket', args=[ticket.id])
    payload = {'email': target_email}
    response = user_client.post(url, payload, follow=True)

    assert response.status_code == 200
    ticket.refresh_from_db()
    assert ticket.user == target_user


def test_assigning_ticket_to_inactive_user_displays_error(user_client):
    ticket = create_valid_ticket_for_user_and_fare(user=user_client.user)
    target_user = factories.UserFactory(is_active=False)
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


def test_frozen_ticket_not_shown_in_dashboard(user_client):
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


def test_frozen_ticket_cannot_be_assigned(user_client):
    ticket = create_valid_ticket_for_user_and_fare(user=user_client.user)
    ticket.frozen = True
    ticket.save()

    url = reverse('user_panel:assign_ticket', args=[ticket.id])
    response = user_client.get(url)

    assert response.status_code == 403


def test_frozen_ticket_cannot_be_managed(user_client):
    ticket = create_valid_ticket_for_user_and_fare(user=user_client.user)
    ticket.frozen = True
    ticket.save()

    url = reverse('user_panel:manage_ticket', args=[ticket.id])
    response = user_client.get(url)

    assert response.status_code == 403


def test_other_fares_tickets_can_be_reassigned(user_client):
    fare = factories.FareFactory(ticket_type=FARE_TICKET_TYPES.other, conference=settings.CONFERENCE_CONFERENCE)
    ticket = create_valid_ticket_for_user_and_fare(user=user_client.user, fare=fare)
    target_user = factories.UserFactory()
    target_email = target_user.email

    url = reverse('user_panel:assign_ticket', args=[ticket.id])
    payload = {'email': target_email}
    response = user_client.post(url, payload, follow=True)

    assert response.status_code == 200
    ticket.refresh_from_db()
    assert ticket.user == target_user


def test_other_fares_tickets_cannot_be_managed(user_client):
    get_default_conference()
    ticket = factories.TicketFactory(user=user_client.user, fare__ticket_type=FARE_TICKET_TYPES.other)
    target_user = factories.UserFactory()
    target_email = target_user.email

    url = reverse('user_panel:manage_ticket', args=[ticket.id])
    payload = {'email': target_email}
    response = user_client.post(url, payload, follow=True)

    assert response.status_code == 403


def test_assigning_resets_tickets(user_client):
    ticket = create_valid_ticket_for_user_and_fare(user=user_client.user)
    asignee = factories.UserFactory()

    url = reverse('user_panel:assign_ticket', args=[ticket.id])
    payload = {'email': asignee.email}
    response = user_client.post(url, payload, follow=True)

    assert response.status_code == 200
    ticket.refresh_from_db()
    assert ticket.user == asignee
    new_tc = TicketConference()  # won't save this, used just to compare with defaults
    assert ticket.p3_conference.shirt_size == new_tc.shirt_size
    assert ticket.p3_conference.diet == new_tc.diet
    assert ticket.p3_conference.tagline == new_tc.tagline
    assert ticket.p3_conference.days == new_tc.days


def test_profile_settings_requires_login(client):
    url = reverse('user_panel:profile_settings')

    response = client.get(url)

    assert redirects_to(response, reverse("accounts:login"))


def test_profile_settings_gets_initial_data(user_client):
    url = reverse('user_panel:profile_settings')
    user = user_client.user
    attendee_profile = user.attendeeprofile
    p3_profile = attendee_profile.p3_profile

    response = user_client.get(url)

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/user_panel/profile_settings.html")
    assert user.first_name in response.content.decode()
    assert user.last_name in response.content.decode()
    assert user.email in response.content.decode()
    assert p3_profile.tagline in response.content.decode()
    assert p3_profile.twitter in response.content.decode()
    assert attendee_profile.getBio().body in response.content.decode()


def test_profile_settings_updates_user_data(user_client):
    url = reverse('user_panel:profile_settings')
    payload = dict(
        first_name='One',
        last_name='Two',
        gender='x',
        email='one@two.three',
        tagline='I am the one',
        twitter='one',
        bio='One to the Two',
    )

    response = user_client.post(url, data=payload)

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/user_panel/profile_settings.html")
    assert payload['first_name'] in response.content.decode()
    assert payload['last_name'] in response.content.decode()
    assert payload['gender'] in response.content.decode()
    assert payload['email'] in response.content.decode()
    assert payload['tagline'] in response.content.decode()
    assert payload['twitter'] in response.content.decode()
    assert payload['bio'] in response.content.decode()


def test_profile_settings_forbids_using_registered_email(user_client):
    url = reverse('user_panel:profile_settings')
    user = user_client.user
    original_email = user.email
    another_user = make_user()
    payload = dict(
        email=another_user.email,
    )

    response = user_client.post(url, data=payload)

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/user_panel/profile_settings.html")
    user.refresh_from_db()
    assert user.email == original_email


def test_profile_settings_update_show_no_image(user_client):
    """
    4 scenarios to test - show no image, show gravatar, show url, show image.
    """
    url = reverse('user_panel:profile_settings')
    user = user_client.user
    attendee_profile = user.attendeeprofile
    p3_profile = attendee_profile.p3_profile
    required_fields = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "gender": "x",
    }

    # Show no image
    response = user_client.post(url, data=required_fields)

    assert response.status_code == 200
    attendee_profile.refresh_from_db()
    p3_profile.refresh_from_db()
    assert not attendee_profile.image
    assert p3_profile.image_url == ""
    assert p3_profile.image_gravatar is False


def test_profile_settings_update_show_url_image(user_client):
    url = reverse('user_panel:profile_settings')
    user = user_client.user
    attendee_profile = user.attendeeprofile
    p3_profile = attendee_profile.p3_profile
    required_fields = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "gender": "x",
    }

    # Provide image url
    response = user_client.post(url, data={
        **required_fields,
        "picture_options": PICTURE_CHOICES.url,
        "image_url": "https://epstage.europython.eu",
    })

    assert response.status_code == 200
    attendee_profile.refresh_from_db()
    p3_profile.refresh_from_db()
    assert not attendee_profile.image
    assert p3_profile.image_url != ""
    assert p3_profile.image_gravatar is False


def test_profile_settings_update_use_gravatar(user_client):
    url = reverse('user_panel:profile_settings')
    user = user_client.user
    attendee_profile = user.attendeeprofile
    p3_profile = attendee_profile.p3_profile
    required_fields = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "gender": "x",
    }

    # Use gravatar
    response = user_client.post(url, data={
        **required_fields,
        "picture_options": PICTURE_CHOICES.gravatar
    })

    assert response.status_code == 200
    attendee_profile.refresh_from_db()
    p3_profile.refresh_from_db()
    assert not attendee_profile.image
    assert p3_profile.image_url == ""
    assert p3_profile.image_gravatar is True


def test_profile_settings_update_use_uploaded_image(user_client):
    url = reverse('user_panel:profile_settings')
    user = user_client.user

    required_fields = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "gender": "x",
    }

    # Upload an image
    response = user_client.post(url, data={
        **required_fields,
        "picture_options": PICTURE_CHOICES.file,
        "image": SimpleUploadedFile('image.jpg', 'here be images'.encode()),
    })

    assert response.status_code == 200

    user.refresh_from_db()
    attendee_profile = user.attendeeprofile
    p3_profile = attendee_profile.p3_profile

    attendee_profile.refresh_from_db()
    p3_profile.refresh_from_db()

    assert attendee_profile.image
    assert p3_profile.image_url == ""
    assert p3_profile.image_gravatar is False
