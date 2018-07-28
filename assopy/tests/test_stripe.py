from django.core.urlresolvers import reverse
from django.test import TestCase
from mock import Mock
from mock import patch
from django_factory_boy import auth as auth_factories

from assopy.models import User, Order
from assopy.tests.factories.order import CreditCardOrderFactory


class StripeViewTestCase(TestCase):
    def setUp(self):
        auth_user = auth_factories.UserFactory(password='demo')
        is_logged = self.client.login(username=auth_user.username,
                                      password='demo')
        self.assertTrue(is_logged)

        self.user = User.objects.create(user=auth_user)

    @patch('assopy.stripe.views.StripeCheckoutView.get_object')
    @patch('stripe.Charge.create')
    @patch('email_template.utils.email')
    @patch('django.core.mail.send_mail')
    def test_add_stripe_on_order_test(self, send_email, email, create, get_object):
        data = {
            'stripeToken': '1234567890',
            'stripeEmail': 'demo@demo.org',
            'stripeTokenType': '1111',
        }

        charge = Mock(id='1')

        order = CreditCardOrderFactory()

        get_object.return_value = order
        create.return_value = charge

        url = reverse('assopy-stripe-checkout', kwargs={'pk': order.id})
        response = self.client.post(url, data=data, follow=True)
        self.assertEqual(response.status_code, 200)

        order = Order.objects.get(id=order.id)
        self.assertEqual(order.stripe_charge_id, charge.id)

    @patch('assopy.stripe.views.StripeCheckoutView.get_object')
    @patch('email_template.utils.email')
    @patch('django.core.mail.send_mail')
    def test_stripe_get(self, send_email, email, get_object):
        order = CreditCardOrderFactory()
        get_object.return_value = order
        url = reverse('assopy-stripe-checkout', kwargs={'pk': order.id})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('assopy-stripe-success'),
                             fetch_redirect_response=False)

