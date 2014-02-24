# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('p3.views',
    url(r'^map.js/', 'map_js', name='p3-map-js'),
    url(r'^cart/$', 'cart', name='p3-cart'),
    url(r'^cart/calculator/$', 'calculator', name='p3-calculator'),
    url(r'^billing/$', 'billing', name='p3-billing'),
    url(r'^tickets/$', 'tickets', name='p3-tickets'),
    url(r'^tickets/(?P<tid>\d+)/$', 'ticket', name='p3-ticket'),
    url(r'^user/(?P<token>.{36})/$', 'user', name='p3-user'),

    url(r'^secure_media/(?P<path>.*)', 'secure_media', name='p3-secure-media'),

    url(r'^sprint-submission/$', 'sprint_submission', name='p3-sprint-submission'),
    url(r'^sprints/$', 'sprints', name='p3-sprints'),
    url(r'^sprints/(?P<sid>\d+)/$', 'sprint', name='p3-sprint'),

    url(r'^sim_report/$', 'sim_report', name='p3-sim-report'),
    url(r'^hotel_report/$', 'hotel_report', name='p3-hotel-report'),

    url(r'^p/profile/(?P<slug>[\w-]+)/$', 'p3_profile', name='p3-profile'),
    url(r'^p/profile/(?P<slug>[\w-]+)/avatar$', 'p3_profile_avatar', name='p3-profile-avatar'),
    url(r'^p/profile/(?P<slug>[\w-]+).json$', 'p3_profile', name='p3-profile-json', kwargs={'format_': 'json'}),
    url(r'^p/profile/(?P<slug>[\w-]+)/message$', 'p3_profile_message', name='p3-profile-message'),

    url(r'^p/account/data$', 'p3_account_data', name='p3-account-data'),
    url(r'^p/account/email$', 'p3_account_email', name='p3-account-email'),
    url(r'^p/account/spam_control$', 'p3_account_spam_control', name='p3-account-spam-control'),

    url(r'^whos-coming$', 'whos_coming', name='p3-whos-coming', kwargs={'conference': None}),
    url(r'^(?P<conference>[\w-]+)/whos-coming$', 'whos_coming', name='p3-whos-coming-conference'),

    url(r'^live/$', 'live', name='p3-live'),
    url(r'^live/events$', 'live_events', name='p3-live-events'),
    url(r'^live/(?P<track>[\w-]+)/$', 'live_track', name='p3-live-track'),
    url(r'^live/(?P<track>[\w-]+)/video$', 'live_track_video', name='p3-live-track-video'),
    url(r'^live/(?P<track>[\w-]+)/events$', 'live_track_events', name='p3-live-track-events'),
)

urlpatterns += patterns('p3.views',
    url(r'^schedule/(?P<conference>[\w-]+)/$', 'schedule', name='p3-schedule'),
    url(r'^schedule/(?P<conference>[\w-]+).ics$', 'schedule_ics', name='p3-schedule-ics'),

    url(r'^schedule/(?P<conference>[\w-]+)/my-schedule/$',
        'my_schedule', name='p3-schedule-my-schedule'),
    url(r'^schedule/(?P<conference>[\w-]+)/my-schedule.ics$',
        'schedule_ics', name='p3-schedule-my-schedule-ics', kwargs={'mode': 'my-schedule'}),

    url(r'^schedule/(?P<conference>[\w-]+)/list/$',
        'schedule_list', name='p3-schedule-list'),

    url(r'^my-schedule/$', 'jump_to_my_schedule', name='p3-my-schedule'),
)

urlpatterns += patterns('p3.views',
    url(r'^legacy/invoice/(?P<assopy_id>.+)/$', 'genro_invoice_pdf', name='genro-legacy-invoice'),
)
