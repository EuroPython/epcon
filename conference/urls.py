# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^speakers/(?P<slug>[\w-]+).xml', 'conference.views.speaker_xml', name = 'conference-speaker-xml'),
    url(r'^speakers/(?P<slug>[\w-]+)', 'conference.views.speaker', name = 'conference-speaker'),
    url(r'^speaker/admin/image_upload', 'conference.views.speaker_admin_image_upload', name = 'conference-speaker-img-upload'),
    url(r'^talks/admin/upload', 'conference.views.talk_admin_upload', name = 'conference-talks-upload'),
    url(r'^talks/report', 'conference.views.talk_report', name = 'conference-talk-report'),
    url(r'^talks/(?P<slug>[\w-]+).xml$', 'conference.views.talk_xml', name = 'conference-talk-xml'),
    url(r'^talks/(?P<slug>[\w-]+)$', 'conference.views.talk', name = 'conference-talk'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>[^\.]*).xml/speakers.xml$', 'conference.views.schedule_speakers_xml', name = 'conference-schedule-speakers-xml'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>[^\.]*).xml/?$', 'conference.views.schedule_xml', name = 'conference-schedule-xml'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>[^\.]*)$', 'conference.views.schedule', name = 'conference-schedule'),
    url(r'^places/', 'conference.views.places', name = 'conference-places'),
    url(r'^sponsors/(?P<sponsor>.*)/', 'conference.views.sponsor', name = 'conference-sponsor'),
    url(r'^(?P<conference>.*)/talks.xml$', 'conference.views.talks_xml', name = 'conference-talks-xml'),
    url(r'^paper-submission/$', 'conference.views.paper_submission', name='conference-paper-submission'),
    url(r'^voting/$', 'conference.views.voting', name='conference-voting'),
)

