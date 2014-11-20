from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from .views import StripeCheckoutView, StripeSuccessView

urlpatterns = patterns(
    '',
    url(r'checkout/(?P<pk>\d+)/$', StripeCheckoutView.as_view(), name='assopy-stripe-checkout'),
    url(r'success/$', StripeSuccessView.as_view(), name='assopy-stripe-success'),
)
