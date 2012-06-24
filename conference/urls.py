# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('conference.views',
    url(r'^p/(?P<slug>[\w-]+)/?$', 'user_profile', name='conference-profile'),
    url(r'^u/(?P<uuid>[\w]{6})/?$', 'user_profile_link', name='conference-profile-link'),

    url(r'^myself$', 'myself_profile', name='conference-myself-profile'),

    url(r'^speakers/(?P<slug>[\w-]+).xml', 'speaker_xml', name='conference-speaker-xml'),
    url(r'^speakers/(?P<slug>[\w-]+)', 'speaker', name='conference-speaker'),

    url(r'^talks/report', 'talk_report', name='conference-talk-report'),
    url(r'^talks/(?P<slug>[\w-]+)/video$', 'talk_video', name='conference-talk-video'),
    url(r'^talks/(?P<slug>[\w-]+)/video.mp4$', 'talk_video', name='conference-talk-video-mp4'),
    url(r'^talks/(?P<slug>[\w-]+).xml$', 'talk_xml', name='conference-talk-xml'),
    url(r'^talks/(?P<slug>[\w-]+)$', 'talk', name='conference-talk'),
    url(r'^talks/(?P<slug>[\w-]+)/preview$', 'talk_preview', name='conference-talk-preview'),

    url(r'^places/', 'places', name='conference-places'),
    url(r'^sponsors/(?P<sponsor>.*)/', 'sponsor', name='conference-sponsor'),
    url(r'^paper-submission/$', 'paper_submission', name='conference-paper-submission'),
    url(r'^voting/$', 'voting', name='conference-voting'),

    url(r'^(?P<conference>[\w-]+).xml/$', 'conference_xml', name='conference-data-xml'),
)

urlpatterns += patterns('conference.views',
    url(r'^schedule/(?P<conference>.*)/(?P<slug>[\w-]+)/$',
        'schedule', name='conference-schedule'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>[\w-]+).xml/?$',
        'schedule_xml', name='conference-schedule-xml'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>[\w-]+)/(?P<eid>\d+)/interest$',
        'schedule_event_interest', name='conference-schedule-event-interest'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>[\w-]+)/(?P<eid>\d+)/booking$',
        'schedule_event_booking', name='conference-schedule-event-booking'),
    url(r'^schedule/(?P<conference>.*)/events/booking$',
        'schedule_events_booking_status', name='conference-schedule-events-booking-status'),
    url(r'^schedule/(?P<conference>.*)/events/expected_attendance$',
        'schedule_events_expected_attendance', name='conference-schedule-events-expected-attendance'),
)

urlpatterns += patterns('conference.views',
    url(r'^(?P<conference>[\w-]+)/covers$',
        'covers', name='conference-covers'),
)
