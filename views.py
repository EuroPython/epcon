# -*- coding: UTF-8 -*-
import urllib
from conference import models
from django.conf import settings
from django.http import Http404
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404

def speaker(request, slug):
    spk = get_object_or_404(models.Speaker, slug = slug)
    return render_to_response(
        'conference/speaker.html', { 'speaker': spk },
        context_instance = RequestContext(request))

def talk(request, slug):
    tlk = get_object_or_404(models.Talk, slug = slug)
    return render_to_response(
        'conference/talk.html', { 'talk': tlk },
        context_instance = RequestContext(request))

def talk_report(request):
    conference = request.GET.get('conference')
    tags = request.GET.getlist('tag')
    return render_to_response(
        'conference/talk_report.html', {
            'conference': conference,
            'tags': tags,
        },
        context_instance = RequestContext(request))

def schedule(request, conference, slug):
    sch = get_object_or_404(models.Schedule, conference = conference, slug = slug)
    return render_to_response(
        'conference/schedule.html', { 'schedule': sch },
        context_instance = RequestContext(request))

def genro_wrapper(request):
    """
    mostra in un iframe l'applicazione conference di genropy
    """
    try:
        conf = dict(settings.GNR_CONFERENCE)
    except AttributeError:
        raise Http404()
    conf['src'] += '?' + urllib.urlencode(request.GET)
    return render_to_response(
        'conference/genro_wrapper.html', conf,
        context_instance = RequestContext(request))

