from django.conf.urls import url
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from conference.models import Talk


def talk(request, talk_slug):
    """
    Display Talk
    """
    talk = get_object_or_404(Talk, slug=talk_slug)
    talk_as_dict = dump_relevant_talk_information_to_dict(talk)

    return TemplateResponse(
        request,
        "ep19/bs/talks/talk.html",
        {
            "title": talk.title,
            "talk": talk,
            "talk_as_dict": talk_as_dict,
            "social_image_url": request.build_absolute_uri(
                reverse("conference-talk-social-card-png", kwargs={"slug": talk.slug})
            ),
        },
    )


def dump_relevant_talk_information_to_dict(talk: Talk):

    output = {
        "title": talk.title,
        "uuid": talk.uuid,
        "slug": talk.slug,
        "type": talk.type,
        "type_display": talk.get_type_display(),
        "subtitle": talk.sub_title,
        "abstract_short": talk.abstract_short,
        "abstract": talk.get_abstract(),
        "abstract_extra": talk.abstract_extra,
        "python_level": talk.get_level_display(),
        "domain_level": talk.get_domain_level_display(),
        "created": talk.created,
        "modified": talk.modified,
        "admin_type": talk.admin_type,
        "status": talk.status,
        "tags": [t.name for t in talk.tags.all()],
        "speakers": [],
    }

    for speaker in talk.get_all_speakers():
        ap = speaker.user.attendeeprofile
        output["speakers"].append(
            {
                "id": speaker.user.id,
                "name": speaker.user.assopy_user.name(),
                "email": speaker.user.email,
                "company": ap.company,
                "company_homepage": ap.company_homepage,
                "bio": getattr(ap.getBio(), "body", ""),
                "phone": ap.phone,
                "slug": ap.slug,
            }
        )

    return output


urlpatterns = [url(r"^(?P<talk_slug>[\w-]+)/$", talk, name="talk")]
