# coding: utf-8

from __future__ import unicode_literals, absolute_import

from django.conf import settings as dsettings
from django.conf.urls import url, include
from django.contrib.auth.views import (
    login,
    logout,
    password_change,
    password_change_done,
    password_reset,
    password_reset_done,
    password_reset_confirm,
    password_reset_complete,
)

from assopy.forms import LoginForm, SetPasswordForm


urlpatterns = [
    url(r'^login/$',
        login,
        kwargs={'authentication_form': LoginForm},
        name="login"),

    url(r'^logout/$', logout, name="logout"),

    # Password change
    url(r'^password_change/$', password_change, name='password_change'),
    url(r'^password_change/done/$', password_change_done,
        name='password_change_done'),

    # Password reset, using default django views.
    url(r'^password_reset/$', password_reset, name='password_reset'),

    url(r'^password_reset/done/$', password_reset_done,
        name='password_reset_done'),

    url(r'^reset/(?P<uidb64>[\w-]+)/(?P<token>[\w]{1,13}-[\w]{1,20})/$',
        password_reset_confirm,
        kwargs={'set_password_form': SetPasswordForm},
        name='password_reset_confirm'),

    url(r'^reset/done/$', password_reset_complete,
        name='password_reset_complete'),


    # New account
    url(r'^new-account/$', 'assopy.views.new_account',
        name='assopy-new-account'),
    url(r'^new-account/feedback$', 'assopy.views.new_account_feedback',
        name='assopy-new-account-feedback'),

    # Manage user profile
    url(r'^profile/$', 'assopy.views.profile', name='assopy-profile'),
    url(r'^profile/identities$', 'assopy.views.profile_identities', name='assopy-profile-identities'),
    url(r'^billing/$', 'assopy.views.billing', name='assopy-billing'),
    url(r'^janrain/login-mismatch/$', 'assopy.views.janrain_login_mismatch', name='assopy-janrain-login_mismatch'),
    url(r'^janrain/token/$', 'assopy.views.janrain_token', name='assopy-janrain-token'),
    url(r'^janrain/incomplete-profile/$', 'assopy.views.janrain_incomplete_profile', name='assopy-janrain-incomplete-profile'),
    url(r'^janrain/incomplete-profile/feedback$', 'assopy.views.janrain_incomplete_profile_feedback', name='assopy-janrain-incomplete-profile-feedback'),
    url(r'^otc/(?P<token>.{36})/$', 'assopy.views.otc_code', name='assopy-otc-token'),
    url(r'^checkout/$', 'assopy.views.checkout', name='assopy-checkout'),
    url(r'^tickets/$', 'assopy.views.tickets', name='assopy-tickets'),

    url(r'^geocode/$', 'assopy.views.geocode', name='assopy-geocode'),

    url(r'orders/(?P<order_id>\d+)/(?P<item_id>\d+)/voucher$', 'assopy.views.voucher', name='assopy-orderitem-voucher'),
    url(r'orders/(?P<order_id>\d+)/(?P<item_id>\d+)/refund$', 'assopy.views.refund', name='assopy-orderitem-refund'),
    url(r'orders/(?P<assopy_id>.+)/completed$', 'assopy.views.order_complete', name='assopy-order-complete'),
    url(r'bank_return/(?P<code>.+)/$', 'assopy.views.bank_feedback_ok', name='assopy-bank-feedback-ok'),

    url(
        r'orders/(?P<order_code>.+)/invoices/(?P<code>.+).html$',
        'assopy.views.invoice',
        name='assopy-invoice-html',
        kwargs={'mode': 'html'},
    ),
    url(
        r'orders/(?P<order_code>.+)/invoices/(?P<code>.+).pdf$',
        'assopy.views.invoice',
        name='assopy-invoice-pdf',
        kwargs={'mode': 'pdf'},
    ),

    url(
        r'orders/(?P<order_code>.+)/credit-note/(?P<code>.+).html$',
        'assopy.views.credit_note',
        name='assopy-credit_note-html',
        kwargs={'mode': 'html'},
    ),
    url(
        r'orders/(?P<order_code>.+)/credit-note/(?P<code>.+).pdf$',
        'assopy.views.credit_note',
        name='assopy-credit_note-pdf',
        kwargs={'mode': 'pdf'},
    ),
]

if 'assopy.stripe' in dsettings.INSTALLED_APPS:
    urlpatterns += [
        url(r'^stripe/', include('assopy.stripe.urls')),
    ]
