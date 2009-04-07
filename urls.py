# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^speakers/(?P<slug>.*)', 'conference.views.speaker', name = 'conference-speaker'),
    url(r'^talks/admin/upload', 'conference.views.talk_admin_upload', name = 'conference-talks-upload'),
    url(r'^talks/report', 'conference.views.talk_report', name = 'conference-talk-report'),
    url(r'^talks/(?P<slug>.*)', 'conference.views.talk', name = 'conference-talk'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>.*)', 'conference.views.schedule', name = 'conference-schedule'),
    url(r'^hotels/', 'conference.views.hotels', name = 'conference-hotels'),
)

