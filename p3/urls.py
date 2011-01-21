# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^map.js/', 'p3.views.map_js', name='p3-map-js'),
)
