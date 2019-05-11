
from django.conf.urls import url
from conference import views as conf_views

urlpatterns = [
    url(r'^p/(?P<slug>[\w-]+)/?$',
        conf_views.user_profile,
        name='conference-profile'),

    url(r'^u/(?P<uuid>[\w]{6})/?$',
        conf_views.user_profile_link,
        name='conference-profile-link'),

    url(r'^u/(?P<uuid>[\w]{6})/message?$',
        conf_views.user_profile_link_message,
        name='conference-profile-link-message'),

    url(r'^my_conferences/$',
        conf_views.user_conferences,
        name='conference-profile-conferences'),

    url(r'^myself$',
        conf_views.myself_profile,
        name='conference-myself-profile'),

    url(r'^speakers/(?P<slug>[\w-]+).xml',
        conf_views.speaker_xml,
        name='conference-speaker-xml'),

    url(r'^speakers/(?P<slug>[\w-]+)',
        conf_views.speaker,
        name='conference-speaker'),

    url(r'^talks/report',
        conf_views.talk_report,
        name='conference-talk-report'),

    url(r'^talks/(?P<slug>[\w-]+)/video$',
        conf_views.talk_video,
        name='conference-talk-video'),

    url(r'^talks/(?P<slug>[\w-]+)/video.mp4$',
        conf_views.talk_video,
        name='conference-talk-video-mp4'),

    url(r'^talks/(?P<slug>[\w-]+).xml$',
        conf_views.talk_xml,
        name='conference-talk-xml'),

    url(r'^talks/(?P<slug>[\w-]+)$',
        conf_views.talk,
        name='conference-talk'),

    url(r'^talks/(?P<slug>[\w-]+)/preview$',
        conf_views.talk_preview,
        name='conference-talk-preview'),

    url(r'^talks/(?P<slug>[\w-]+)/social-card.png$',
        conf_views.talk_social_card_png,
        name='conference-talk-social-card-ong'),

    url(r'^sponsors/(?P<sponsor>.*)',
        conf_views.sponsor_json,
        name='conference-sponsor-json'),

    url(r'^paper-submission/$',
        conf_views.paper_submission,
        name='conference-paper-submission'),

    url(r'^cfp/thank-you/$',
        conf_views.cfp_thank_you_for_proposal,
        name='cfp-thank-you-for-proposal'),

    # url(r'^voting/$',
        # conf_views.voting,
        # name='conference-voting'),
]

urlpatterns += [
    url(r'^(?P<conference>[\w-]+).xml/$',
        conf_views.conference_xml,
        name='conference-data-xml'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>[\w-]+)/$',
        conf_views.schedule,
        name='conference-schedule'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>[\w-]+).xml/?$',
        conf_views.schedule_xml,
        name='conference-schedule-xml'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>[\w-]+)/(?P<eid>\d+)/interest$', # NOQA
        conf_views.schedule_event_interest,
        name='conference-schedule-event-interest'),
    url(r'^schedule/(?P<conference>.*)/(?P<slug>[\w-]+)/(?P<eid>\d+)/booking$',
        conf_views.schedule_event_booking,
        name='conference-schedule-event-booking'),
    url(r'^schedule/(?P<conference>.*)/events/booking$',
        conf_views.schedule_events_booking_status,
        name='conference-schedule-events-booking-status'),
    url(r'^schedule/(?P<conference>.*)/events/expected_attendance$',
        conf_views.schedule_events_expected_attendance,
        name='conference-schedule-events-expected-attendance'),
]

urlpatterns += [
    url(r'^(?P<conference>[\w-]+)/covers$',
        conf_views.covers,
        name='conference-covers'),
]
