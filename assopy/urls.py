from django.conf.urls.defaults import *
from assopy.forms import LoginForm, PasswordResetForm, SetPasswordForm

urlpatterns = patterns('',
    url(r'^login/$', 'django.contrib.auth.views.login', kwargs={ 'authentication_form': LoginForm }),
    url(r'^logout/$', 'django.contrib.auth.views.logout'),
    url(r'^password_change/$', 'django.contrib.auth.views.password_change'),
    url(r'^password_change/done/$', 'django.contrib.auth.views.password_change_done'),
    url(r'^password_reset/$', 'django.contrib.auth.views.password_reset', kwargs={ 'password_reset_form': PasswordResetForm }),
    url(r'^password_reset/done/$', 'django.contrib.auth.views.password_reset_done'),
    url(r'^reset/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', 'django.contrib.auth.views.password_reset_confirm', kwargs={ 'set_password_form': SetPasswordForm }),
    url(r'^reset/done/$', 'django.contrib.auth.views.password_reset_complete'),

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

    url(r'paypal_return/$', 'assopy.views.paypal_feedback_ok', name='assopy-paypal-feedback-ok'),
    url(r'bank_return/$', 'assopy.views.bank_feedback_ok', name='assopy-bank-feedback-ok'),
)
