
from django.conf.urls import url

from p3 import views as p3_views


urlpatterns = [
    url(r'^cart/$', p3_views.cart, name='p3-cart'),
    url(r'^cart/calculator/$', p3_views.calculator, name='p3-calculator'),
    url(r'^billing/$', p3_views.billing, name='p3-billing'),
    url(r'^tickets/$', p3_views.tickets, name='p3-tickets'),
    url(r'^tickets/(?P<tid>\d+)/$', p3_views.ticket, name='p3-ticket'),
    url(r'^user/(?P<token>.{36})/$', p3_views.user, name='p3-user'),

    url(r'^p/profile/(?P<slug>[\w-]+)/$', p3_views.p3_profile, name='p3-profile'),
    url(r'^p/profile/(?P<slug>[\w-]+)/avatar$', p3_views.p3_profile_avatar, name='p3-profile-avatar'),
    url(r'^p/profile/(?P<slug>[\w-]+).json$', p3_views.p3_profile, name='p3-profile-json', kwargs={'format_': 'json'}),
    url(r'^p/profile/(?P<slug>[\w-]+)/message$', p3_views.p3_profile_message, name='p3-profile-message'),

    url(r'^p/account/data$', p3_views.p3_account_data, name='p3-account-data'),
    url(r'^p/account/email$', p3_views.p3_account_email, name='p3-account-email'),
    url(r'^p/account/spam_control$', p3_views.p3_account_spam_control, name='p3-account-spam-control'),

    url(r'^whos-coming$', p3_views.whos_coming, name='p3-whos-coming', kwargs={'conference': None}),
    url(r'^(?P<conference>[\w-]+)/whos-coming$', p3_views.whos_coming, name='p3-whos-coming-conference'),

    url(r'^live/$', p3_views.live, name='p3-live'),
    url(r'^live/events$', p3_views.live_events, name='p3-live-events'),
    url(r'^live/(?P<track>[\w-]+)/$', p3_views.live_track, name='p3-live-track'),
    url(r'^live/(?P<track>[\w-]+)/video$', p3_views.live_track_video, name='p3-live-track-video'),
    url(r'^live/(?P<track>[\w-]+)/events$', p3_views.live_track_events, name='p3-live-track-events'),
]


urlpatterns += [
    url(r'^schedule/(?P<conference>[\w-]+)/$', p3_views.schedule, name='p3-schedule'),
    url(r'^schedule/(?P<conference>[\w-]+).ics$', p3_views.schedule_ics, name='p3-schedule-ics'),

    url(r'^schedule/(?P<conference>[\w-]+)/my-schedule/$',
        p3_views.my_schedule, name='p3-schedule-my-schedule'),
    url(r'^schedule/(?P<conference>[\w-]+)/my-schedule.ics$',
        p3_views.schedule_ics, name='p3-schedule-my-schedule-ics', kwargs={'mode': 'my-schedule'}),

    url(r'^schedule/(?P<conference>[\w-]+)/list/$',
        p3_views.schedule_list, name='p3-schedule-list'),

    url(r'^my-schedule/$', p3_views.jump_to_my_schedule, name='p3-my-schedule'),
]
