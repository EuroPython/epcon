from django.conf.urls import url

from conference import views
from conference.views.social_card import talk_social_card_png


urlpatterns = [
    url(r"^talks/(?P<slug>[\w-]+)$", views.talk, name="conference-talk"),
    url(
        r"^talks/(?P<slug>[\w-]+)/social-card.png$",
        talk_social_card_png,
        name="conference-talk-social-card-png",
    ),
]
