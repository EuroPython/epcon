from django.conf import settings as dsettings
from django.conf.urls import patterns, url, include
from django.contrib import auth
from assopy.forms import LoginForm, SetPasswordForm

urlpatterns = patterns('',
    url(r'^login/$', 'django.contrib.auth.views.login', kwargs={ 'authentication_form': LoginForm }),
    url(r'^logout/$', 'django.contrib.auth.views.logout'),
    url(r'^password_change/$', 'django.contrib.auth.views.password_change', name='password_change'),
    url(r'^password_change/done/$', 'django.contrib.auth.views.password_change_done', name='password_change_done'),
    url(r'^password_reset/$', 'django.contrib.auth.views.password_reset', kwargs={ 'password_reset_form': auth.forms.PasswordResetForm }, name='assopy-password-reset'),
    url(r'^password_reset/done/$', 'django.contrib.auth.views.password_reset_done', name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', 'django.contrib.auth.views.password_reset_confirm', kwargs={ 'set_password_form': SetPasswordForm }, name='password_reset_confirm'),
    url(r'^reset/done/$', 'django.contrib.auth.views.password_reset_complete', name='password_reset_complete'),

    url(r'^new-account/$', 'assopy.views.new_account', name='assopy-new-account'),
    url(r'^new-account/feedback$', 'assopy.views.new_account_feedback', name='assopy-new-account-feedback'),
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
    url(r'^paypal/redirect/(?P<code>.+)/$','assopy.views.paypal_billing', name='assopy-paypal-redirect'),
    url(r'^paypal/cc/redirect/(?P<code>.+)/$','assopy.views.paypal_cc_billing', name='assopy-cc-paypal-redirect'),

    url(r'paypal_return/(?P<code>.+)/$', 'assopy.views.paypal_feedback_ok', name='assopy-paypal-feedback-ok'),
    url(r'^paypal/cancel/(?P<code>.+)/$','assopy.views.paypal_cancel', name='assopy-paypal-feedback-cancel'),
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
)

if 'paypal.standard.ipn' in dsettings.INSTALLED_APPS:
    urlpatterns += patterns('',
        url(r'^paypal/standard-ipn/', include('paypal.standard.ipn.urls')),
    )

if 'assopy.stripe' in dsettings.INSTALLED_APPS:
    urlpatterns += patterns(
        '', url(r'^stripe/', include('assopy.stripe.urls')),
    )
