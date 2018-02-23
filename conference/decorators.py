import functools

from django import http
from django.shortcuts import get_object_or_404, redirect

from conference import models, settings


def speaker_access(f): # pragma: no cover
    """
    Decorator that protects the view relative to a speaker.
    """
    @functools.wraps(f)
    def wrapper(request, slug, **kwargs):
        spk = get_object_or_404(models.Speaker, slug=slug)
        if request.user.is_staff or request.user == spk.user:
            full_access = True
            talks = spk.talks()
        else:
            full_access = False
            conf = models.Conference.objects.current()
            if settings.VOTING_OPENED(conf, request.user):
                if settings.VOTING_ALLOWED(request.user):
                    talks = spk.talks()
                else:
                    if settings.VOTING_DISALLOWED:
                        return redirect(settings.VOTING_DISALLOWED)
                    else:
                        raise http.Http404()
            else:
                talks = spk.talks(status='accepted')
                if talks.count() == 0:
                    raise http.Http404()

        return f(request, slug, speaker=spk, talks=talks, full_access=full_access, **kwargs)
    return wrapper


def talk_access(f): # pragma: no cover
    """
    Decorator that protects the view relative to a talk.
    """
    @functools.wraps(f)
    def wrapper(request, slug, **kwargs):
        tlk = get_object_or_404(models.Talk, slug=slug)
        if request.user.is_anonymous():
            full_access = False
        elif request.user.is_staff:
            full_access = True
        else:
            try:
                tlk.get_all_speakers().get(user__id=request.user.id)
            except (models.Speaker.DoesNotExist, models.Speaker.MultipleObjectsReturned):
                # The MultipleObjectsReturned can happen if the user is not logged on and .id is None
                full_access = False
            else:
                full_access = True

        # if the talk is unconfirmed can access:
        #   * superusers or speakers (full access = True)
        #   * if the community voting is in progress who has the right to vote
        if tlk.status == 'proposed' and not full_access:
            conf = models.Conference.objects.current()
            if not settings.VOTING_OPENED(conf, request.user):
                return http.HttpResponseForbidden()
            if not settings.VOTING_ALLOWED(request.user):
                if settings.VOTING_DISALLOWED:
                    return redirect(settings.VOTING_DISALLOWED)
                else:
                    return http.HttpResponseForbidden()

        return f(request, slug, talk=tlk, full_access=full_access, **kwargs)
    return wrapper


def profile_access(f): # pragma: no cover
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
                if not (settings.VOTING_OPENED(conf, request.user) and settings.VOTING_ALLOWED(request.user)):
                    if profile.visibility == 'x':
                        return http.HttpResponseForbidden()
                    elif profile.visibility == 'm' and request.user.is_anonymous():
                        return http.HttpResponseForbidden()
        return f(request, slug, profile=profile, full_access=full_access, **kwargs)
    return wrapper