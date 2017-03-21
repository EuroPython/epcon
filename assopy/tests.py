"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""
from mock import patch
from mock import Mock
from django.test import TestCase
from assopy.models import User, Order
from django.contrib.auth.models import User as AuthUser
from django.core.urlresolvers import reverse


class AddStripeInOrderTest(TestCase):
    @patch('assopy.stripe.views.StripeCheckoutView.get_object')
    @patch('stripe.Charge.create')
    @patch('email_template.utils.email')
    def test_stripe(self, email, create, get_object):
        data = {
            'stripeToken': '1234567890',
            'stripeEmail': 'demo@demo.org',
            'stripeTokenType': '1111',
        }

        auth_user = AuthUser.objects.create_user('admin', 'admin@demo.org', 'demo')
        auth_user.save()

        response = self.client.login(username='admin', password='demo')

        self.assertTrue(response)

        user = User.objects.create(user=auth_user)

        charge = Mock(id='1')
        email.return_value = Mock()

        order = Order.objects.create(user=user,
                                     payment='cc',  ## cc because stripe is a credit card.
                                     items=[])

        get_object.return_value = order
        create.return_value = charge

        url = reverse('assopy-stripe-checkout', kwargs={'pk': 12345})
        response = self.client.post(url, data=data, follow=True)
        self.assertEqual(response.status_code, 200)

        order = Order.objects.get(id=order.id)
        self.assertEqual(order.stripe_charge_id, charge.id)


class ResetPasswordTestCase(TestCase):
    def test_reset_password(self):
        url = reverse('password_reset_confirm',
                      kwargs={
                          'uidb64': '12123313A',
                          'token': 'a0-1212dd'
                      })

        response = self.client.get(url)

        self.assertTemplateUsed(response, 'registration/password_reset_confirm.html')
