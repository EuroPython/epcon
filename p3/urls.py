from django.conf.urls import url

from p3 import views as p3_views


urlpatterns = [
    url(r'^p/profile/(?P<slug>[\w-]+)/avatar$', p3_views.p3_profile_avatar, name='p3-profile-avatar'),

    url(r'^live/$', p3_views.live, name='p3-live'),
    url(r'^live/events$', p3_views.live_events, name='p3-live-events'),
    url(r'^live/(?P<track>[\w-]+)/$', p3_views.live_track, name='p3-live-track'),
    url(r'^live/(?P<track>[\w-]+)/video$', p3_views.live_track_video, name='p3-live-track-video'),
    url(r'^live/(?P<track>[\w-]+)/events$', p3_views.live_track_events, name='p3-live-track-events'),
]
