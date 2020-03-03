import functools

from django import http
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect

from conference import models


def full_profile_required(func):
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        if (request.user
                and request.user.id  # FIXME test mocks mess with the above object so we have to check the id
                and (not request.user.attendeeprofile or not request.user.attendeeprofile.gender)):

            messages.warning(
                request,
                "Please update your profile to continue using the EuroPython website."
            )

            return redirect(reverse('user_panel:profile_settings'))

        return func(request, *args, **kwargs)
    return wrapper


def profile_access(f):  # pragma: no cover
    """
    Decorator which protect the relative view to a profile.
    """
    @functools.wraps(f)
    def wrapper(request, slug, **kwargs):
        try:
            profile = models.AttendeeProfile.objects\
                .select_related('user')\
                .get(slug=slug)
        except models.AttendeeProfile.DoesNotExist:
            raise http.Http404()

        if request.user.is_staff or request.user == profile.user:
            full_access = True
        else:
            full_access = False
            # if the profile belongs to a speaker with talk of "accepted" is visible
            # whatever you say the same profile.
            accepted = models.TalkSpeaker.objects\
                .filter(speaker__user=profile.user)\
                .filter(talk__status='accepted')\
                .count()
            if not accepted:
                # if the community voting is open and the profile belongs to a speaker
                # with the talk in the race page is visible
                conf = models.Conference.objects.current()
                if not (settings.CONFERENCE_VOTING_OPENED(conf, request.user) and settings.CONFERENCE_VOTING_ALLOWED(request.user)):  # noqa
                    if profile.visibility == 'x':
                        return http.HttpResponseForbidden()
                    elif profile.visibility == 'm' and request.user.is_anonymous:
                        return http.HttpResponseForbidden()
        return f(request, slug, profile=profile, full_access=full_access, **kwargs)
    return wrapper
