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

from django.core.urlresolvers import reverse
from django.utils import timezone

from django_factory_boy import auth as auth_factories
from pytest import mark

from assopy.models import Invoice, Order, Vat
from assopy.tests.factories.user import UserFactory as AssopyUserFactory
from conference.models import AttendeeProfile

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


@mark.django_db
def test_assopy_profile(client):
    profile_url = reverse('assopy-profile')
    user = auth_factories.UserFactory(email='joedoe@example.com',
                                      is_active=True)
    # both are required to access user profile page.
    AssopyUserFactory(user=user)
    AttendeeProfile.objects.create(user=user, slug='foobar')

    client.login(email='joedoe@example.com', password='password123')
    response = client.get(profile_url)

    make_sure_root_template_is_used(response, "assopy/profile.html")
    make_sure_root_template_is_used(response, "assopy/base.html")
    make_sure_root_template_is_used(response, "p3/base.html")

    # there are some includes used in this template, namely
    # profile_{email_contact,personal_data,spam_control}.html
    # those templates are also used in specific p3 views

    make_sure_root_template_is_used(
        response, "assopy/profile_email_contact.html")
    make_sure_root_template_is_used(
        response, "assopy/profile_personal_data.html")
    make_sure_root_template_is_used(
        response, "assopy/profile_spam_control.html")

    # also those templates are used in some p3 views, so adding some additional
    # checks for them.
    p3_account_spam_control_url = reverse('p3-account-spam-control')
    response = client.get(p3_account_spam_control_url)
    make_sure_root_template_is_used(response,
                                    "assopy/profile_spam_control.html")

    p3_account_email_url = reverse('p3-account-email')
    response = client.get(p3_account_email_url)
    make_sure_root_template_is_used(response,
                                    "assopy/profile_email_contact.html")

    p3_account_data_url = reverse('p3-account-data')
    response = client.get(p3_account_data_url)
    make_sure_root_template_is_used(response,
                                    "assopy/profile_personal_data.html")
