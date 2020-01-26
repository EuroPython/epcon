# coding: utf-8

"""
This is a (temporary?) module with tests regarding template structure around
assopy and p3 apps. Basically the situation right now (2017-11-08) is such that
we have multiple places where assopy and p3 templates are stored, and it's not
clear which template (and especially which inheritance path) is being used.

The main goal of this is to clean up the location and inheritance structure, so
that it's easier to figure out which template is being used.
"""



from datetime import date
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from django_factory_boy import auth as auth_factories
from pytest import mark

from assopy.models import Invoice, Order, Vat
from conference.models import AttendeeProfile

from tests.common_tools import template_paths
from tests.factories import AssopyUserFactory


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
        html='Here goes full html',
        exchange_rate_date=date.today(),
    )

    invoice_url = reverse('assopy-invoice-html', kwargs={
        'order_code': order_code,
        'code': invoice_code,
    })

    response = client.get(invoice_url)
    # TODO(artcz) after we changed to pre-rendering and storing full html of
    # the invoice we no longer use a template in this view.
    # TBD if we need that test here anymore, since it supposed to test
    # templates temporarily anyway.
    assert response.content == b'Here goes full html'
