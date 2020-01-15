from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from common.decorators import render_to_json
from conference import models
from conference.decorators import profile_access


def talk(request, slug):
    return redirect('talks:talk', permanent=True, talk_slug=slug)


@render_to_json
def sponsor_json(request, sponsor):
    """
    Returns the data of the requested sponsor
    """
    sponsor = get_object_or_404(models.Sponsor, slug=sponsor)
    return {
        'sponsor': sponsor.sponsor,
        'slug': sponsor.slug,
        'url': sponsor.url
    }


@profile_access
def user_profile(request, slug, profile=None, full_access=False):
    return redirect('profiles:profile', profile_slug=slug)


@login_required
def myself_profile(request):
    p = models.AttendeeProfile.objects.getOrCreateForUser(request.user)
    return redirect('conference-profile', slug=p.slug)
