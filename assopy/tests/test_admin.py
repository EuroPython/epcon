from unittest import mock
from pytest import mark

from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse
from django_factory_boy import auth as auth_factories

from assopy.stripe.tests import factories
from conference.tests.factories.conference import ConferenceFactory


@mark.django_db
def test_country_list_admin(admin_client):
    factories.CountryFactory()
    url = reverse('admin:assopy_country_changelist')

    response = admin_client.get(url)

    assert response.status_code == 200


def test_coupon_list_admin(admin_client):
    url = reverse('admin:assopy_coupon_changelist')

    response = admin_client.get(url)

    assert response.status_code == 200


def test_invoice_list_admin(admin_client):
    url = reverse('admin:assopy_invoice_changelist')

    response = admin_client.get(url)

    assert response.status_code == 200


def test_invoicelog_list_admin(admin_client):
    url = reverse('admin:assopy_invoicelog_changelist')

    response = admin_client.get(url)

    assert response.status_code == 200


@mark.django_db
def test_order_list_admin(admin_client):
    fare = factories.FareFactory()
    factories.OrderFactory(items=[(fare, {"qty": 1})])
    url = reverse('admin:assopy_order_changelist')

    response = admin_client.get(url)

    assert response.status_code == 200


@mark.django_db
def test_order_invoices_admin(admin_client):
    fare = factories.FareFactory()
    order = factories.OrderFactory(items=[(fare, {"qty": 1})])
    url = reverse('admin:assopy-edit-invoices')

    response = admin_client.get(url, data={'id': order.id})

    assert response.status_code == 200


@mark.django_db
def test_order_stats_admin(admin_client):
    ConferenceFactory()
    url = reverse('admin:assopy-order-stats')

    response = admin_client.get(url)

    assert response.status_code == 200


@mark.django_db
def test_order_vouchers_admin(admin_client):
    factories.FareFactory(conference=settings.CONFERENCE_CONFERENCE, payment_type='v')
    url = reverse('admin:assopy-order-vouchers')

    response = admin_client.get(url)

    assert response.status_code == 200


@mark.django_db
def test_order_vouchers_fare_admin(admin_client):
    fare = factories.FareFactory()
    ticket = factories.TicketFactory(fare=fare, frozen=False)
    order = factories.OrderFactory(items=[(fare, {"qty": 1})])
    order._complete = True
    order_item = factories.OrderItemFactory(order=order, ticket=ticket, price=1)

    url = reverse('admin:assopy-order-vouchers-fare', kwargs={
        'conference': order_item.ticket.fare.conference,
        'fare': order_item.ticket.fare.code,
    })

    response = admin_client.get(url)

    assert response.status_code == 200


@mark.django_db
def test_vat_list_admin(admin_client):
    factories.VatFactory()
    url = reverse('admin:assopy_vat_changelist')

    response = admin_client.get(url)

    assert response.status_code == 200


@mark.django_db
def test_user_new_order_admin(admin_client):
    assopy_user = factories.AssopyUserFactory()
    url = reverse('admin:auser-order', kwargs={'uid': assopy_user.user.id})

    response = admin_client.get(url)

    assert response.status_code == 200


@mark.django_db
def test_user_send_verification_email(admin_client):
    user = auth_factories.UserFactory()
    
    user.is_active = False
    user.save()

    url = reverse('admin:auser-send-verification-email', kwargs={'uid': user.id})

    with mock.patch('assopy.admin.get_current_site') as current_site_mock:
        with mock.patch('assopy.admin.send_verification_email') as send_mock:
            response = admin_client.get(url)

    send_mock.assert_called_once_with(user, current_site_mock.return_value)
    assert response.status_code == 302


@mark.django_db
def test_user_send_verification_email_to_active_user(admin_client):
    user = auth_factories.UserFactory()
    
    user.is_active = True
    user.save()

    url = reverse('admin:auser-send-verification-email', kwargs={'uid': user.id})

    with mock.patch('assopy.admin.send_verification_email') as send_mock:
        response = admin_client.get(url)

    assert not send_mock.called
    assert response.status_code == 302
