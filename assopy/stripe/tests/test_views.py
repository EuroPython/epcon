from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase, LiveServerTestCase
from django.utils import timezone

from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait

import stripe

from assopy.models import Order

from . import factories as f


class TestCheckoutDetailView(TestCase):
    """
    Tests the stripe checkout detail view. Only GET method
    """
    def setUp(self):
        self.john = f.AssopyUserFactory()

        # clean fares
        from conference.models import Fare
        Fare.objects.all().delete()

    def get_token(self):
        stripe.api_key = settings.STRIPE_PUBLISHABLE_KEY
        token = stripe.Token.create(
            card={
                "number": '4242424242424242',
                "exp_month": 12,
                "exp_year": 2030,
                "cvc": '123'
            },
        )
        return token

    def test_checkout_get_fails_without_login(self):
        """
        Tests the view redirects to login url when user is not authenticated
        """
        fare = f.FareFactory()
        order = f.OrderFactory(items=[(fare, {"qty": 1})])

        checkout_url = reverse("assopy-stripe-checkout", args=(order.pk,))
        response = self.client.get(checkout_url)

        redirect_url = settings.LOGIN_URL + "?next=" + checkout_url
        self.assertRedirects(response, redirect_url, target_status_code=404)

    def test_checkout_get_fails_when_order_does_not_belong_to_user(self):
        """
        Tests the view fails (404) when order does not belong to current user
        """
        self.client.login(username=self.john.user.username, password="123456")

        fare = f.FareFactory()
        # this order does not belong to john
        order = f.OrderFactory(items=[(fare, {"qty": 1})])

        checkout_url = reverse("assopy-stripe-checkout", args=(order.pk,))
        response = self.client.get(checkout_url)

        self.assertEqual(response.status_code, 404)

    def test_checkout_get_fails_when_order_payment_already_completed(self):
        """
        Tests the view redirects to the success page when order payment is already completed
        """
        self.client.login(username=self.john.user.username, password="123456")

        fare = f.FareFactory()
        order = f.OrderFactory(user=self.john, items=[(fare, {"qty": 1})])
        order.confirm_order(timezone.now())

        checkout_url = reverse("assopy-stripe-checkout", args=(order.pk,))
        response = self.client.get(checkout_url)

        self.assertRedirects(response, reverse("assopy-stripe-success"))

    def test_checkout_get_redirects_to_success_when_total_is_zero(self):
        """
        Tests the view confirm the order and redirects to the success page
        when the order total amount is 0
        """
        self.client.login(username=self.john.user.username, password="123456")

        fare = f.FareFactory(price=0)
        order = f.OrderFactory(user=self.john, items=[(fare, {"qty": 1})])

        checkout_url = reverse("assopy-stripe-checkout", args=(order.pk,))
        response = self.client.get(checkout_url)

        self.assertRedirects(response, reverse("assopy-stripe-success"))
        self.assertTrue(Order.objects.filter(pk=order.pk).filter(_complete=True))

    def test_checkout_get_works(self):
        """
        Tests the view is working properly
        """
        self.client.login(username=self.john.user.username, password="123456")

        fare = f.FareFactory()
        order = f.OrderFactory(user=self.john, items=[(fare, {"qty": 1})])

        checkout_url = reverse("assopy-stripe-checkout", args=(order.pk,))
        response = self.client.get(checkout_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "assopy/stripe/checkout.html")

        url = reverse("assopy-stripe-checkout", args=(order.pk,))
        self.assertContains(response, '<form action="%s" method="POST">' % url)
        self.assertContains(response, '"https://checkout.stripe.com/checkout.js" class="stripe-button"')
        self.assertContains(response, 'data-key="pk_test_qRUg4tJTFJgUiLz0FxKnuOXO"')
        self.assertContains(response, 'data-amount="1000"')
        self.assertContains(response, 'data-name="Foo Bar"')
        self.assertContains(response, 'data-description="%s"' % order.orderitem_set.all()[0].description)
        self.assertContains(response, 'data-image="foo-bar-logo-url"')

    def test_checkout_post_fails_without_login(self):
        """
        Tests the view redirects to login url when user is not authenticated
        """
        fare = f.FareFactory()
        order = f.OrderFactory(user=self.john, items=[(fare, {"qty": 1})])

        checkout_url = reverse("assopy-stripe-checkout", args=(order.pk,))
        response = self.client.post(checkout_url)

        redirect_url = settings.LOGIN_URL + "?next=" + checkout_url
        self.assertRedirects(response, redirect_url, target_status_code=404)

    def test_checkout_post_fails_when_order_does_not_belong_to_user(self):
        """
        Tests the view fails (404) when order does not belong to current user
        """
        self.client.login(username=self.john.user.username, password="123456")

        fare = f.FareFactory()
        # this order does not belong to john
        order = f.OrderFactory(items=[(fare, {"qty": 1})])

        checkout_url = reverse("assopy-stripe-checkout", args=(order.pk,))
        response = self.client.post(checkout_url)

        self.assertEqual(response.status_code, 404)

    def test_checkout_post_fails_when_order_payment_already_completed(self):
        """
        Tests the view fails (404) when order have been paid
        """
        self.client.login(username=self.john.user.username, password="123456")

        fare = f.FareFactory()
        order = f.OrderFactory(user=self.john, items=[(fare, {"qty": 1})])
        order.confirm_order(timezone.now())

        checkout_url = reverse("assopy-stripe-checkout", args=(order.pk,))
        response = self.client.post(checkout_url)

        self.assertEqual(response.status_code, 404)

    def test_checkout_post_confirms_the_order_with_a_valid_token(self):
        """
        Test the payment is charged with success when token is valid
        """
        self.client.login(username=self.john.user.username, password="123456")

        fare = f.FareFactory()
        order = f.OrderFactory(user=self.john, items=[(fare, {"qty": 1})])

        token = self.get_token()

        data = {
            "stripeToken": token.id,
            "stripeTokenType": token.type,
            "stripeEmail": "foo@bar.com",
        }
        checkout_url = reverse("assopy-stripe-checkout", args=(order.pk,))
        response = self.client.post(checkout_url, data)

        self.assertRedirects(response, reverse("assopy-stripe-success"))
        self.assertTrue(Order.objects.filter(pk=order.pk).filter(_complete=True))


class TestLiveStripeCheckoutPayment(LiveServerTestCase):
    """
    Tests the payment flow through the stripe checkout view.
    """
    fixtures = ['user-data.json']

    @classmethod
    def setUpClass(cls):
        cls.selenium = WebDriver()
        super(TestLiveStripeCheckoutPayment, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(TestLiveStripeCheckoutPayment, cls).tearDownClass()

    def setUp(self):
        self.john = f.AssopyUserFactory()

        # clean fares
        from conference.models import Fare
        Fare.objects.all().delete()

    def login(self, username, password):
        """
        Login with the webdriver
        """
        self.client.login(username=username, password=password)
        cookie = self.client.cookies['sessionid']

        # selenium will set cookie domain based on current page domain
        self.selenium.get(self.live_server_url + reverse("django.contrib.auth.views.login"))
        self.selenium.add_cookie({'name': 'sessionid', 'value': cookie.value, 'secure': False, 'path': '/'})
        self.selenium.refresh()  # need to update page for logged in user

    def stripe_token(self):
        """
        Obtain stripe token to charge
        """
        # open the stripe checkout form
        stripe_pay_button = self.selenium.find_element_by_class_name("stripe-button-el")
        stripe_pay_button.click()

        # move to the proper iframe
        self.selenium.switch_to.frame("stripe_checkout_app")

        email_input = self.selenium.find_element_by_id("email")
        email_input.send_keys("foo@bar.com")
        card_number_input = self.selenium.find_element_by_id("card_number")
        card_number_input.send_keys("4012")
        card_number_input.send_keys("8888")
        card_number_input.send_keys("8888")
        card_number_input.send_keys("1881")

        cc_exp_input = self.selenium.find_element_by_id("cc-exp")
        cc_exp_input.send_keys("12")
        cc_exp_input.send_keys("30")

        cc_csc_input = self.selenium.find_element_by_id("cc-csc")
        cc_csc_input.send_keys("333")

        submit_button = self.selenium.find_element_by_id("submitButton")
        submit_button.click()

    def test_order_charge_completed_with_success(self):
        self.login(username=self.john.user.username, password="123456")

        fare = f.FareFactory()
        order = f.OrderFactory(user=self.john, items=[(fare, {"qty": 1})])

        checkout_url = reverse("assopy-stripe-checkout", args=(order.pk,))
        self.selenium.get('%s%s' % (self.live_server_url, checkout_url))

        # fill the stripe form and submit
        self.stripe_token()

        # wait for the redirect
        success_url = '%s%s' % (self.live_server_url, reverse("assopy-stripe-success"))
        
        class current_url_is_equal_to(object):
            def __init__(self, url):
                self.url = url

            def __call__(self, driver):
                return driver.current_url == self.url

        WebDriverWait(self.selenium, 20).until(
            current_url_is_equal_to(success_url)
        )

        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order._complete, True)
