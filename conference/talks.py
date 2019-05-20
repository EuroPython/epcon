from django.conf.urls import url
from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from conference.models import Talk, TALK_STATUS, TALK_TYPE_CHOICES


def talk(request, talk_slug):
    """
    Display Talk
    """
    talk = get_object_or_404(Talk, slug=talk_slug)
    talk_as_dict = dump_relevant_talk_information_to_dict(talk)

    return TemplateResponse(
        request,
        "ep19/bs/talks/talk.html",
        {"title": talk.title, "talk": talk, "talk_as_dict": talk_as_dict},
    )


def list_accepted_talks_for_current_conference(request):
    """
    """
    # Copy from conference/talk_vorting.py;
    # Possibly could be refactored to use some function to come up with filters
    talk_type = request.GET.get("talk_type", "all")
    extra_filters = []
    if talk_type == "talk":
        extra_filters += [
            Q(
                type__in=[
                    TALK_TYPE_CHOICES.t_30,
                    TALK_TYPE_CHOICES.t_45,
                    TALK_TYPE_CHOICES.t_60,
                ]
            )
        ]
    if talk_type == "training":
        extra_filters += [Q(type__in=[TALK_TYPE_CHOICES.r_180])]
    if talk_type == "poster":
        extra_filters += [
            Q(
                type__in=[
                    TALK_TYPE_CHOICES.i_60,
                    TALK_TYPE_CHOICES.p_180,
                    TALK_TYPE_CHOICES.n_60,
                    TALK_TYPE_CHOICES.n_90,
                ]
            )
        ]
    if talk_type == "helpdesk":
        extra_filters += [Q(type__in=[TALK_TYPE_CHOICES.h_180])]

    talks = get_accepted_talks_for_current_conference(extra_filters)

    return TemplateResponse(
        request,
        "ep19/bs/talks/list_accepted_talks.html",
        {"talks": talks, "talk_type": talk_type}
    )


def get_accepted_talks_for_current_conference(extra_filters):
    return (
        Talk.objects
        .filter(
            conference=settings.CONFERENCE_CONFERENCE,
            status=TALK_STATUS.accepted
        )
        .filter(*extra_filters)
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
        "abstract": talk.getAbstract().body,
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
            }
        )

    return output


urlpatterns = [
    url(r"^$", list_accepted_talks_for_current_conference, name="list"),
    url(r"^(?P<talk_slug>[\w-]+)/$", talk, name="talk"),
]
