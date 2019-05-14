from django import http
from django.template.loader import render_to_string

from conference.decorators import talk_access
from weasyprint import HTML


@talk_access
def talk_social_card_png(request, slug, talk, full_access):
    content = render_to_string(
        "ep19/bs/conference/talk_social_card.html",
        {"title": talk.title, "subtitle": "Patrick"},
    )

    data = HTML(
        string=content, base_url=request.build_absolute_uri("/")
    ).write_png()

    return http.HttpResponse(data, content_type="image/png")
