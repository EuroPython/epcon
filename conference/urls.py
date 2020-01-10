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

urlpatterns += [
    url(
        r"^schedule/(?P<conference>.*)/(?P<slug>[\w-]+)/$",
        views.schedule,
        name="conference-schedule",
    ),
    url(
        r"^schedule/(?P<conference>.*)/(?P<slug>[\w-]+)/(?P<eid>\d+)/interest$",  # NOQA
        views.schedule_event_interest,
        name="conference-schedule-event-interest",
    ),
    url(
        r"^schedule/(?P<conference>.*)/(?P<slug>[\w-]+)/(?P<eid>\d+)/booking$",
        views.schedule_event_booking,
        name="conference-schedule-event-booking",
    ),
    url(
        r"^schedule/(?P<conference>.*)/events/booking$",
        views.schedule_events_booking_status,
        name="conference-schedule-events-booking-status",
    ),
    url(
        r"^schedule/(?P<conference>.*)/events/expected_attendance$",
        views.schedule_events_expected_attendance,
        name="conference-schedule-events-expected-attendance",
    ),
]

urlpatterns += [
    url(
        r"^(?P<conference>[\w-]+)/covers$",
        views.covers,
        name="conference-covers",
    )
]
