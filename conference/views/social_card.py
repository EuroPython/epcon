from django import http
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from weasyprint import HTML

from conference.models import Talk


def talk_social_card_png(request, slug):
    talk = get_object_or_404(Talk, slug=slug)

    subtitle = ", ".join(
        [
            speaker.user.assopy_user.name()
            for speaker in talk.speakers.all().select_related(
                "user__assopy_user"
            )
        ]
    )

    content = render_to_string(
        "ep19/bs/conference/talk_social_card.html",
        {"title": talk.title, "subtitle": subtitle},
    )

    data = HTML(
        string=content, base_url=request.build_absolute_uri("/")
    ).write_png()

    return http.HttpResponse(data, content_type="image/png")
