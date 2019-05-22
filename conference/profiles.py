from django.conf import settings
from django.conf.urls import url
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from conference.models import (
    AttendeeProfile,
    Conference,
    Talk,
    ATTENDEEPROFILE_VISIBILITY,
)
from conference.talk_voting import is_user_allowed_to_vote


def profile(request, profile_slug):
    """
    Display profile details.
    """
    speaker_profile = get_object_or_404(AttendeeProfile, slug=profile_slug)

    if not profile_page_visible(profile=speaker_profile, for_user=request.user):
        return TemplateResponse(request, "ep19/bs/profiles/profile_unavailable.html")

    return TemplateResponse(
        request,
        "ep19/bs/profiles/profile.html",
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
            "talks": speaker_profile.user.speaker.talks().filter(
                conference=settings.CONFERENCE_CONFERENCE
            ),
            "speaker_avatar": speaker_profile.p3_profile.public_profile_image_url,
        },
    )


def profile_page_visible(profile, for_user):
    """
    Page should be accessible if:
    * trying to access own profile
    * voting is open and current user can vote
    * or profile has an accepted talk in current conference
    * or the profile is set as public
    * or profile is set as visible to participants and current user is authenticated
    """
    conference = Conference.objects.current()

    if profile.visibility == ATTENDEEPROFILE_VISIBILITY.PUBLIC:
        return True

    if for_user.is_authenticated:
        if profile.pk == for_user.attendeeprofile.pk:
            return True

        if (
            conference.voting()
            and is_user_allowed_to_vote(for_user)
            and Talk.objects.proposed()
            .filter(conference=conference.code, speakers__user__in=[profile.user])
            .exists()
        ):
            return True

        if (
            Talk.objects.accepted()
            .filter(conference=conference.code, speakers__user__in=[profile.user])
            .exists()
        ):
            return True

        if profile.visibility == ATTENDEEPROFILE_VISIBILITY.PARTICIPANTS_ONLY:
            return True

    return False


urlpatterns = [url(r"^(?P<profile_slug>[\w-]+)/$", profile, name="profile")]
