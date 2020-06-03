from django.conf.urls import url as re_path
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse

from conference.models import Conference, Talk, TALK_STATUS
from conference.forms import TalkUpdateForm, TalkSlidesForm


def talk(request, talk_slug):
    """
    Display Talk
    """
    talk = get_object_or_404(Talk, slug=talk_slug)
    talk_as_dict = dump_relevant_talk_information_to_dict(talk)

    can_update_talk = request.user.is_authenticated and can_user_update_talk(
        user=request.user, talk=talk
    )
    can_submit_slides = request.user.is_authenticated and can_user_submit_talk_slides(
        user=request.user, talk=talk
    )

    return TemplateResponse(
        request,
        "conference/talks/talk.html",
        {
            "title": talk.title,
            "talk": talk,
            "talk_as_dict": talk_as_dict,
            "social_image_url": request.build_absolute_uri(
                reverse("conference:conference-talk-social-card-png", kwargs={"slug": talk.slug})
            ),
            "can_update_talk": can_update_talk,
            "can_submit_slides": can_submit_slides,
        },
    )


@login_required
def update_talk(request, talk_slug):
    """
    Update talk if you're the author.
    """
    talk = get_object_or_404(Talk, slug=talk_slug)

    if not can_user_update_talk(user=request.user, talk=talk):
        return HttpResponseForbidden()

    talk_update_form = TalkUpdateForm(instance=talk)

    if request.method == "POST":
        talk_update_form = TalkUpdateForm(request.POST, instance=talk)

        if talk_update_form.is_valid():
            talk_update_form.save(request.user)
            messages.success(request, "Talk details updated")
            return redirect(talk.get_absolute_url())
        else:
            messages.error(request, "Please correct the errors below")

    return TemplateResponse(
        request,
        "conference/talks/update_talk.html",
        {"talk": talk, "talk_update_form": talk_update_form},
    )


@login_required
def submit_slides(request, talk_slug):
    """
    Submit talk slides.
    """
    talk = get_object_or_404(Talk, slug=talk_slug)

    if not can_user_submit_talk_slides(user=request.user, talk=talk):
        return HttpResponseForbidden()

    talk_slides_form = TalkSlidesForm(instance=talk)

    if request.method == "POST":
        talk_slides_form = TalkSlidesForm(instance=talk, data=request.POST, files=request.FILES)

        if talk_slides_form.is_valid():
            talk_slides_form.save()
            messages.success(request, "Slides submitted successfully")
            return redirect(talk.get_absolute_url())
        else:
            messages.error(request, "Please correct the errors below")

    return TemplateResponse(
        request,
        "conference/talks/update_talk.html",
        {"talk": talk, "talk_update_form": talk_slides_form},
    )


def can_user_update_talk(user, talk):
    """
    Check if the user can update the given talk.
    """
    conf = Conference.objects.current()

    return (
        (talk.created_by == user or is_user_a_speaker_for_the_talk(user, talk))
        and talk.status == TALK_STATUS.accepted
        and not conf.has_finished
    )


def is_user_a_speaker_for_the_talk(user, talk):
    speakers = talk.get_all_speakers()
    for speaker in speakers:
        if speaker.user == user:
            return True
    return False


def can_user_submit_talk_slides(user, talk):
    """
    Check if the user can upload talk slides.
    """
    return (
        (talk.created_by == user or is_user_a_speaker_for_the_talk(user, talk))
        and talk.status == TALK_STATUS.accepted
    )


def dump_relevant_talk_information_to_dict(talk: Talk, speaker_tickets=None):

    """ Dumps information about talk to a dictionary suitable for sending
        back as JSON.
        
        speaker_tickets may be given as dictionary mapping assigned to email
        to Ticket object and is used for defining has_ticket.
        
    """
    event = talk.get_event()
    if event is not None:
        event = event.json_dump()
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
        "event": event,
        "schedule_url": talk.get_schedule_url(),
        "slides_url": talk.get_slides_url(),
    }

    for speaker in talk.get_all_speakers():
        ap = speaker.user.attendeeprofile
        if speaker_tickets is not None:
            has_ticket = speaker.user.email in speaker_tickets
        else:
            has_ticket = None
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
                "location": ap.location,
                "has_ticket": has_ticket,
            }
        )

    return output


urlpatterns = [
    re_path(
        r"^(?P<talk_slug>[\w-]+)/update/$",
        update_talk,
        name="update_talk"
    ),
    re_path(
        r"^(?P<talk_slug>[\w-]+)/submit_slides/$",
        submit_slides,
        name="submit_slides"
    ),
    re_path(
        r"^(?P<talk_slug>[\w-]+)/$",
        talk,
        name="talk"
    ),
]
