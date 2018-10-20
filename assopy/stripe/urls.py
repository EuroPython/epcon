from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import url

from .views import StripeCheckoutView, StripeSuccessView

urlpatterns = [
    url(r'checkout/(?P<pk>\d+)/$', StripeCheckoutView.as_view(), name='assopy-stripe-checkout'),
    url(r'success/$', StripeSuccessView.as_view(), name='assopy-stripe-success'),
]
