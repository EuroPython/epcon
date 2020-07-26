import functools

from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect


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
