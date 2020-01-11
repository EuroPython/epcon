from django.conf.urls import url

from conference import views
from conference.views.social_card import talk_social_card_png


urlpatterns = [
    url(
        r"^p/(?P<slug>[\w-]+)/?$",
        views.user_profile,
        name="conference-profile",
    ),
    url(
        r"^speakers/(?P<slug>[\w-]+)", views.speaker, name="conference-speaker"
    ),
    url(r"^talks/report", views.talk_report, name="conference-talk-report"),
    url(
        r"^talks/(?P<slug>[\w-]+)/video$",
        views.talk_video,
        name="conference-talk-video",
    ),
    url(
        r"^talks/(?P<slug>[\w-]+)/video.mp4$",
        views.talk_video,
        name="conference-talk-video-mp4",
    ),
    url(r"^talks/(?P<slug>[\w-]+)$", views.talk, name="conference-talk"),
    url(
        r"^talks/(?P<slug>[\w-]+)/preview$",
        views.talk_preview,
        name="conference-talk-preview",
    ),
    url(
        r"^talks/(?P<slug>[\w-]+)/social-card.png$",
        talk_social_card_png,
        name="conference-talk-social-card-png",
    ),
    url(
        r"^sponsors/(?P<sponsor>.*)",
        views.sponsor_json,
        name="conference-sponsor-json",
    ),
]
