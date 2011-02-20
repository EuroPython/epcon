# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^map.js/', 'p3.views.map_js', name='p3-map-js'),
    url(r'^cart/$', 'p3.views.cart', name='p3-cart'),
    url(r'^tickets/$', 'p3.views.tickets', name='p3-tickets'),
    url(r'^tickets/(?P<tid>\d+)/$', 'p3.views.ticket', name='p3-ticket'),
    url(r'^user/(?P<token>.{36})/$', 'p3.views.user', name='p3-user'),
)
