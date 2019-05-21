from django.conf import settings
from django.conf.urls import url
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from conference.models import AttendeeProfile


def speaker(request, speaker_slug):
    """
    Display Talk
    """
    speaker_profile = get_object_or_404(AttendeeProfile, slug=speaker_slug)

    return TemplateResponse(
        request,
        "ep19/bs/speakers/speaker.html",
        {
            "speaker_name": speaker_profile.user.assopy_user.name(),
            "tagline": speaker_profile.p3_profile.tagline,
            "personal_website": speaker_profile.personal_homepage,
            "location": speaker_profile.location,
            "company": speaker_profile.company,
            "company_website": speaker_profile.company_homepage,
            "job_title": speaker_profile.job_title,
            "twitter": speaker_profile.p3_profile.twitter,
            "bio": speaker_profile.getBio().body,
            "talks": speaker_profile.user.speaker.talks().filter(conference=settings.CONFERENCE_CONFERENCE),
            "speaker_avatar": speaker_profile.p3_profile.public_profile_image_url,
        },
    )


urlpatterns = [url(r"^(?P<speaker_slug>[\w-]+)/$", speaker, name="speaker")]
