from django.conf.urls.defaults import *
from assopy.views import LoginForm

urlpatterns = patterns('',
    url(r'^login/$', 'django.contrib.auth.views.login', kwargs={ 'authentication_form': LoginForm }),
    url(r'^logout/$', 'django.contrib.auth.views.logout'),
    url(r'^password_change/$', 'django.contrib.auth.views.password_change'),
    url(r'^password_change/done/$', 'django.contrib.auth.views.password_change_done'),
    url(r'^password_reset/$', 'django.contrib.auth.views.password_reset'),
    url(r'^password_reset/done/$', 'django.contrib.auth.views.password_reset_done'),
    url(r'^reset/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', 'django.contrib.auth.views.password_reset_confirm'),
    url(r'^reset/done/$', 'django.contrib.auth.views.password_reset_complete'),

    url(r'^home/$', 'assopy.views.home', name='assopy-home'),
)
