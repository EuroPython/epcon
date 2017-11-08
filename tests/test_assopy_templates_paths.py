# coding: utf-8

"""
This is a (temporary?) module with tests regarding template structure around
assopy and p3 apps. Basically the situation right now (2017-11-08) is such that
we have multiple places where assopy and p3 templates are stored, and it's not
clear which template (and especially which inheritance path) is being used.

The main goal of this is to clean up the location and inheritance structure, so
that it's easier to figure out which template is being used.
"""

from __future__ import unicode_literals, absolute_import

from decimal import Decimal

from django.core.urlresolvers import reverse
from django.utils import timezone

from django_factory_boy import auth as auth_factories
from pytest import mark

from assopy.models import Invoice, Order, Vat
from assopy.tests.factories.user import UserFactory as AssopyUserFactory

from tests.common_tools import template_paths


def make_sure_root_template_is_used(response, template_name):
    """
    Checks if templates are used form the root template directory and not from
    p3 or assopy app-templates directories.
    """

    assert response.status_code == 200, response.status_code
    paths = template_paths(response)

    root = "/templates/"
    p3 = "/p3/templates/"
    assopy = "/assopy/templates/"

    assert root + template_name in paths, paths
    assert assopy + template_name not in paths, paths
    assert p3 + template_name not in paths, paths


@mark.django_db
def test_assopy_invoice(client):
    # default password is 'password123' per django_factory_boy
    user = auth_factories.UserFactory(email='joedoe@example.com',
                                      is_active=True)
    assopy_user = AssopyUserFactory(user=user)
    client.login(email='joedoe@example.com', password='password123')

    # invoice_code must be validated via ASSOPY_IS_REAL_INVOICE
    invoice_code, order_code = 'I123', 'asdf'

    # FYI(artcz): Order.objects.create is overloaded method on OrderManager,
    # that sets up a lot of unused stuff, going with manual .save().
    order = Order(user=assopy_user, code=order_code)
    order.save()
    # create some random Vat instance to the invoice creation works
    vat_10 = Vat.objects.create(value=10)

    Invoice.objects.create(
        code=invoice_code,
        order=order,
        emit_date=timezone.now().date(),
        price=Decimal(1337),
        vat=vat_10,
    )

    invoice_url = reverse('assopy-invoice-html', kwargs={
        'order_code': order_code,
        'code': invoice_code,
    })

    response = client.get(invoice_url)
    make_sure_root_template_is_used(response, "assopy/invoice.html")
    make_sure_root_template_is_used(response, "assopy/base_invoice.html")


@mark.django_db
def test_assopy_new_account(client):
    new_account_url = reverse("assopy-new-account")

    response = client.get(new_account_url)
    make_sure_root_template_is_used(response, "assopy/new_account.html")
    make_sure_root_template_is_used(response, "assopy/base.html")
    make_sure_root_template_is_used(response, "p3/base.html")


@mark.django_db
def test_assopy_paypal(client):
    """
    This tests two views – paypal_feedback_ok and paypal_cancel.
    """
    user = auth_factories.UserFactory(email='joedoe@example.com',
                                      is_active=True)
    assopy_user = AssopyUserFactory(user=user)

    order_code = 'asdf'
    order = Order(user=assopy_user, code=order_code, method='paypal')
    order.save()

    paypal_feedback_ok_url = reverse(
        "assopy-paypal-feedback-ok",
        kwargs={'code': order_code}
    )

    paypal_cancel_url = reverse(
        "assopy-paypal-feedback-cancel",
        kwargs={'code': order_code}
    )

    response = client.get(paypal_cancel_url)

    make_sure_root_template_is_used(response, "assopy/paypal_cancel.html")
    make_sure_root_template_is_used(response, "assopy/base.html")
    make_sure_root_template_is_used(response, "p3/base.html")

    # @login_required is not enforced on any of those views, however feedback
    # has some manual checks builtin, so we need to to log in as a correct
    # user.
    client.login(email='joedoe@example.com', password='password123')
    response = client.get(paypal_feedback_ok_url)

    make_sure_root_template_is_used(response, "assopy/paypal_feedback_ok.html")
    make_sure_root_template_is_used(response, "assopy/base.html")
    make_sure_root_template_is_used(response, "p3/base.html")


def test_assopy_profile(client):
    pass
