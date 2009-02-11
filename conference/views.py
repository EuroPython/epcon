# -*- coding: UTF-8 -*-
from conference import models
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404

def speaker(request, slug):
    spk = get_object_or_404(models.Speaker, slug = slug)
    return render_to_response(
        'conference/speaker.html', { 'speaker': spk },
        context_instance = RequestContext(request))
