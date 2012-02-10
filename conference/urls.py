# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('conference.views',
    url(r'^speakers/(?P<slug>[\w-]+).xml', 'speaker_xml', name = 'conference-speaker-xml'),
    url(r'^speakers/(?P<slug>[\w-]+)', 'speaker', name = 'conference-speaker'),
    url(r'^speaker/admin/image_upload', 'speaker_admin_image_upload', name = 'conference-speaker-img-upload'),

    url(r'^talks/admin/upload', 'talk_admin_upload', name = 'conference-talks-upload'),
    url(r'^talks/report', 'talk_report', name = 'conference-talk-report'),
    url(r'^talks/(?P<slug>[\w-]+)/video$', 'talk_video', name = 'conference-talk-video'),
    url(r'^talks/(?P<slug>[\w-]+)/video.mp4$', 'talk_video', name = 'conference-talk-video-mp4'),
    url(r'^talks/(?P<slug>[\w-]+).xml$', 'talk_xml', name = 'conference-talk-xml'),
    url(r'^talks/(?P<slug>[\w-]+)$', 'talk', name = 'conference-talk'),
    url(r'^talks/(?P<slug>[\w-]+)/preview$', 'talk_preview', name = 'conference-talk-preview'),

    url(r'^schedule/(?P<conference>.*)/(?P<slug>[\w-]+).xml/?$', 'schedule_xml', name = 'conference-schedule-xml'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>[\w-]+)/(?P<eid>\d+)/$', 'schedule_event', name = 'conference-schedule-event'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>[\w-]+)/(?P<eid>\d+)/interest$', 'schedule_event_interest', name = 'conference-schedule-event-interest'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>[\w-]+)/$', 'schedule', name = 'conference-schedule'),

    url(r'^places/', 'places', name = 'conference-places'),
    url(r'^sponsors/(?P<sponsor>.*)/', 'sponsor', name = 'conference-sponsor'),
    url(r'^paper-submission/$', 'paper_submission', name='conference-paper-submission'),
    url(r'^voting/$', 'voting', name='conference-voting'),

    url(r'^(?P<conference>[\w-]+).xml/$', 'conference_xml', name = 'conference-data-xml'),
)
