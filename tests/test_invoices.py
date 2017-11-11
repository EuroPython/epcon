# coding: utf-8

from __future__ import unicode_literals, absolute_import

from datetime import date
from decimal import Decimal

from pytest import mark

from django.core.urlresolvers import reverse

from django_factory_boy import auth as auth_factories

# TODO: clean up this import path
from assopy.models import Invoice, Order, Vat
from assopy.tests.factories.user import UserFactory as AssopyUserFactory
from conference.models import AttendeeProfile

from tests.common_tools import template_used


@mark.django_db
def test_591_dont_display_invoices_for_yeras_before_2018(client):
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
