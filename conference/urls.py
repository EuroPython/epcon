# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^speakers/(?P<slug>.*)', 'conference.views.speaker', name = 'conference-speaker'),
    url(r'^talks/(?P<slug>.*)', 'conference.views.talk', name = 'conference-talk'),
)

