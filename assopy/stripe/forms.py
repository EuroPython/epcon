from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms


class StripeCheckoutForm(forms.Form):
    stripeToken = forms.CharField()
    stripeTokenType = forms.CharField()
    stripeEmail = forms.CharField()
