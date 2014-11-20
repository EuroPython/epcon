from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, TemplateView

import stripe

from ..models import Order
from .forms import StripeCheckoutForm


class LoginRequiredMixin(object):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)


class StripeCheckoutView(LoginRequiredMixin, DetailView):
    """
    A view to use the stripe Checkout payment flow
    """
    context_object_name = "order"
    template_name = "assopy/stripe/checkout.html"

    def get_queryset(self):
        qs = Order.objects.filter(user__user=self.request.user)  # get only the orders for the current user
        return qs

    def get(self, request, *args, **kwargs):
        """
        Display the checkout view to pay with stripe
        """
        self.object = self.get_object()

        # the order is already paid so redirect to success page
        if self.object._complete:
            return redirect("assopy-stripe-success")

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """
        Process the form and try to charge the card associated with the token
        """
        # first get the order, excluding the orders that are already paid
        order = self.get_object(self.get_queryset().filter(_complete=False))

        form = StripeCheckoutForm(request.POST)

        stripe_error = None

        # proceed to charge the card
        if form.is_valid():
            # set the stripe secret key
            stripe.api_key = settings.STRIPE_SECRET_KEY

            # get the credit card details submitted by the form
            token = form.cleaned_data['stripeToken']
            email = form.cleaned_data['stripeEmail']

            # amount in cents, and must be an integer
            amount = int(order.total() * 100)

            # Create the charge on Stripe's servers - this will charge the user's card
            try:
                charge = stripe.Charge.create(
                    amount=amount,
                    currency="eur",
                    card=token,
                    description=email
                )
                order.confirm_order(timezone.now())

                # TODO: we should save the charge for future refunds

                # redirect to success page
                return redirect("assopy-stripe-success")

            except stripe.StripeError as e:
                # errors while charging card
                stripe_error = e.json_body["error"]

        # renders the page again with error data
        self.object = order
        context = self.get_context_data(object=self.object, form=form, stripe_error=stripe_error)
        return self.render_to_response(context)


class StripeSuccessView(LoginRequiredMixin, TemplateView):
    template_name = "assopy/stripe/success.html"
