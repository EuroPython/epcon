# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

urlpatterns = patterns('',
    url(r'^map.js/', 'p3.views.map_js', name='p3-map-js'),
    url(r'^cart/$', 'p3.views.cart', name='p3-cart'),
    url(r'^cart/calculator/$', 'p3.views.calculator', name='p3-calculator'),
    url(r'^billing/$', 'p3.views.billing', name='p3-billing'),
    url(r'^tickets/$', 'p3.views.tickets', name='p3-tickets'),
    url(r'^tickets/(?P<tid>\d+)/$', 'p3.views.ticket', name='p3-ticket'),
    url(r'^user/(?P<token>.{36})/$', 'p3.views.user', name='p3-user'),

    url(r'^schedule/(?P<conference>[\w-]+)/$', 'p3.views.schedule', name='p3-schedule'),
    url(r'^schedule/(?P<conference>[\w-]+)/list/$', 'p3.views.schedule_list', name='p3-schedule-list'),
    url(r'^schedule/(?P<conference>[\w-]+)/speakers/$', 'p3.views.schedule_speakers', name='p3-schedule-speakers'),
    url(r'^schedule/(?P<conference>[\w-]+)/my-schedule/$', 'p3.views.my_schedule', name='p3-schedule-my-schedule'),
    url(r'^my-schedule/$', 'p3.views.jump_to_my_schedule', name='p3-my-schedule'),
    url(r'^schedule/(?P<conference>[\w-]+)/schedule.js$', direct_to_template, {'template': 'p3/schedule.js' }, name='p3-schedule-js'),
    url(r'^schedule/(?P<conference>[\w-]+)/search/$', 'p3.views.schedule_search', name='p3-schedule-search'),
    url(r'^secure_media/(?P<path>.*)', 'p3.views.secure_media', name='p3-secure-media'),

    url(r'^sprint-submission/$', 'p3.views.sprint_submission', name='p3-sprint-submission'),
    url(r'^sprints/$', 'p3.views.sprints', name='p3-sprints'),
    url(r'^sprints/(?P<sid>\d+)/$', 'p3.views.sprint', name='p3-sprint'),

    url(r'^sim_report/$', 'p3.views.sim_report', name='p3-sim-report'),
    url(r'^hotel_report/$', 'p3.views.hotel_report', name='p3-hotel-report'),

    url(r'^p/profile/(?P<slug>[\w-]+)/', 'p3.views.p3_profile', name='p3-profile'),
    url(r'^p/account/data', 'p3.views.p3_account_data', name='p3-account-data'),
    url(r'^p/account/email', 'p3.views.p3_account_email', name='p3-account-email'),
    url(r'^p/account/spam_control', 'p3.views.p3_account_spam_control', name='p3-account-spam-control'),

    url(r'^whos-coming$', 'p3.views.whos_coming', name='p3-whos-coming'),
)
