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
    url(r'^profile/$', 'assopy.views.profile', name='assopy-profile'),
    url(r'^billing/$', 'assopy.views.billing', name='assopy-billing'),
    url(r'^janrain/login-mismatch/$', 'assopy.views.janrain_login_mismatch', name='assopy-janrain-login_mismatch'),
    url(r'^janrain/token/$', 'assopy.views.janrain_token', name='assopy-janrain-token'),
    url(r'^otc/(?P<token>.{36})/$', 'assopy.views.otc_code', name='assopy-otc-token'),
    url(r'^checkout/$', 'assopy.views.checkout', name='assopy-checkout'),
    url(r'^tickets/$', 'assopy.views.tickets', name='assopy-tickets'),
)
