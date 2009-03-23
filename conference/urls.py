# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^speakers/(?P<slug>.*)', 'conference.views.speaker', name = 'conference-speaker'),
    url(r'^talks/report', 'conference.views.talk_report', name = 'conference-talk-report'),
    url(r'^talks/(?P<slug>.*)', 'conference.views.talk', name = 'conference-talk'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>.*)', 'conference.views.schedule', name = 'conference-schedule'),
)

