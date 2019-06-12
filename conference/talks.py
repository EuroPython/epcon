from django.conf.urls import url
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse

from conference.models import Conference, Talk, TALK_STATUS
from conference.new_forms import TalkUpdateForm


def talk(request, talk_slug):
    """
    Display Talk
    """
    talk = get_object_or_404(Talk, slug=talk_slug)
    talk_as_dict = dump_relevant_talk_information_to_dict(talk)

    can_update_talk = False
    conf = Conference.objects.current()
    if (
        request.user.is_authenticated
        and talk.created_by == request.user
        and not conf.has_finished
    ):
        can_update_talk = True

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
            "can_update_talk": can_update_talk,
        },
    )


@login_required
def update_talk(request, talk_slug):
    """
    Update talk if you're the author.
    """
    talk = get_object_or_404(Talk, slug=talk_slug)

    if not talk.created_by == request.user or talk.status != TALK_STATUS.accepted:
        return HttpResponseForbidden()

    conf = Conference.objects.current()
    if conf.has_finished:
        return HttpResponseForbidden()

    talk_update_form = TalkUpdateForm(instance=talk)

    if request.method == "POST":
        talk_update_form = TalkUpdateForm(request.POST, instance=talk)

        if talk_update_form.is_valid():
            talk_update_form.save(request.user)
            messages.success(request, "Talk details updated")
            return redirect(talk.get_absolute_url())

    return TemplateResponse(
        request,
        "ep19/bs/talks/update_talk.html",
        {"talk": talk, "talk_update_form": talk_update_form},
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


urlpatterns = [
    url(r"^(?P<talk_slug>[\w-]+)/update/$", update_talk, name="update_talk"),
    url(r"^(?P<talk_slug>[\w-]+)/$", talk, name="talk"),
]
