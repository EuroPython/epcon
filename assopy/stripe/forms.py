


from django import forms


class StripeCheckoutForm(forms.Form):
    stripeToken = forms.CharField()
    stripeTokenType = forms.CharField()
    stripeEmail = forms.CharField()
