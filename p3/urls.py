from django.conf.urls import url

from p3 import views as p3_views


urlpatterns = [
    url(r'^p/profile/(?P<slug>[\w-]+)/$', p3_views.p3_profile, name='p3-profile'),
    url(r'^p/profile/(?P<slug>[\w-]+)/avatar$', p3_views.p3_profile_avatar, name='p3-profile-avatar'),
    url(r'^p/profile/(?P<slug>[\w-]+).json$', p3_views.p3_profile, name='p3-profile-json', kwargs={'format_': 'json'}),
    url(r'^p/profile/(?P<slug>[\w-]+)/message$', p3_views.p3_profile_message, name='p3-profile-message'),

    url(r'^live/$', p3_views.live, name='p3-live'),
    url(r'^live/events$', p3_views.live_events, name='p3-live-events'),
    url(r'^live/(?P<track>[\w-]+)/$', p3_views.live_track, name='p3-live-track'),
    url(r'^live/(?P<track>[\w-]+)/video$', p3_views.live_track_video, name='p3-live-track-video'),
    url(r'^live/(?P<track>[\w-]+)/events$', p3_views.live_track_events, name='p3-live-track-events'),
]


urlpatterns += [
    # url(r'^schedule/(?P<conference>[\w-]+).ics$', p3_views.schedule_ics, name='p3-schedule-ics'),

    # url(r'^schedule/(?P<conference>[\w-]+)/my-schedule/$',
    #     p3_views.my_schedule, name='p3-schedule-my-schedule'),
    # url(r'^schedule/(?P<conference>[\w-]+)/my-schedule.ics$',
    #     p3_views.schedule_ics, name='p3-schedule-my-schedule-ics', kwargs={'mode': 'my-schedule'}),

    # url(r'^schedule/(?P<conference>[\w-]+)/list/$',
    #     p3_views.schedule_list, name='p3-schedule-list'),

    # url(r'^my-schedule/$', p3_views.jump_to_my_schedule, name='p3-my-schedule'),
]
