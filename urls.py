# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^speakers/(?P<slug>.*)', 'conference.views.speaker', name = 'conference-speaker'),
)

