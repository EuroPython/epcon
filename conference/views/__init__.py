from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect


def talk(request, slug):
    return redirect('talks:talk', permanent=True, talk_slug=slug)
