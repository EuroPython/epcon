from __future__ import absolute_import
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.template import Template, Context

from . import factories as f


class TestStripeTemplateTags(TestCase):
    def setUp(self):
        # clean fares
        from conference.models import Fare
        Fare.objects.all().delete()

    def test_stripe_checkout_script_template_tag(self):
        """
        Tests that the 'stripe_checkout_script' template tag works properly
        """
        fare = f.FareFactory()
        order = f.OrderFactory(items=[(fare, {"qty": 1})])

        t = Template("{% load stripe_tags %}{% stripe_checkout_script order %}")
        data = t.render(Context({"order": order}))

        self.assertIn('"https://checkout.stripe.com/checkout.js" class="stripe-button"', data)
        self.assertIn('data-key="pk_test_qRUg4tJTFJgUiLz0FxKnuOXO"', data)
        self.assertIn('data-amount="1000"', data)
        self.assertIn('data-name="Foo Bar"', data)
        self.assertIn('data-description="%s"' % order.orderitem_set.all()[0].description, data)
        self.assertIn('data-image="foo-bar-logo-url"', data)
        self.assertIn('data-currency="EUR"', data)

    def test_stripe_checkout_form_template_tag(self):
        """
        Tests that the 'stripe_checkout_form' template tag works properly
        """
        fare = f.FareFactory()
        order = f.OrderFactory(items=[(fare, {"qty": 1})])

        t = Template("{% load stripe_tags %}{% stripe_checkout_form order %}")
        data = t.render(Context({"order": order}))
        
        url = reverse("assopy-stripe-checkout", args=(order.pk,))
        self.assertIn('<form action="%s" method="POST">' % url, data)
        self.assertIn('"https://checkout.stripe.com/checkout.js" class="stripe-button"', data)
        self.assertIn('data-key="pk_test_qRUg4tJTFJgUiLz0FxKnuOXO"', data)
        self.assertIn('data-amount="1000"', data)
        self.assertIn('data-name="Foo Bar"', data)
        self.assertIn('data-description="%s"' % order.orderitem_set.all()[0].description, data)
        self.assertIn('data-image="foo-bar-logo-url"', data)
        self.assertIn('data-currency="EUR"', data)
