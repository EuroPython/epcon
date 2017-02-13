"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""
import mock
from django.test import TestCase, SimpleTestCase
from assopy.models import User, Order
from django.contrib.auth.models import User as AuthUser
from django.core.urlresolvers import reverse


class AddStripeInOrderTest(TestCase):
    def test_stripe(self):
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

        class Charge(object):
            id = '1'

        with mock.patch('assopy.stripe.views.StripeCheckoutView.get_object') as get_object:
            with mock.patch('stripe.Charge.create') as create:
                with mock.patch('email_template.utils.email') as email:
                    from django.core.mail import EmailMessage
                    email.return_value = EmailMessage()

                    order = Order.objects.create(user=user,
                                                 payment='cc',  ## cc because stripe is a credit card.
                                                 items=[])

                    get_object.return_value = order
                    create.return_value = Charge()

                    url = reverse('assopy-stripe-checkout', kwargs={'pk': 12345})
                    response = self.client.post(url, data=data, follow=True)
                    # print(response)
                    self.assertEqual(response.status_code, 200)

                    order = Order.objects.get(id=order.id)
                    self.assertEqual(order.stripe_charge_id, Charge.id)
