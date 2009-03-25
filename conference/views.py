# -*- coding: UTF-8 -*-
import urllib
from xml.etree import cElementTree as ET
from conference import models
from django.db import transaction
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required

class HttpResponseRedirectSeeOther(HttpResponseRedirect):
    status_code = 303

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

@staff_member_required
@transaction.commit_on_success
def talk_admin_upload(request):
    if request.method != 'POST':
        raise Http404()
    raw = []
    map(raw.append, request.FILES['xml'].chunks())
    tree = ET.fromstring(''.join(raw))
    for spk in tree.findall('talk/speaker'):
        S = {
            'name': spk.find('name').text,
            'homepage': spk.find('homepage').text or '',
            'activity': spk.find('activity').text or '',
            'industry': spk.find('industry').text or '',
            'location': spk.find('location').text or '',
        }
        for bio in spk.findall('bio'):
            S['bio_' + bio.get('lang')] = bio.text or ''
        S['slug'] = slugify(S['name'])
        try:
            speaker = models.Speaker.objects.get(slug = S['slug'])
        except models.Speaker.DoesNotExist:
            speaker = models.Speaker()
            speaker.name = S['name']
            speaker.slug = S['slug']
        if S['homepage'] or not speaker.homepage:
            speaker.homepage = S['homepage']
        if S['activity'] or not speaker.activity:
            speaker.activity = S['activity']
        if S['industry'] or not speaker.industry:
            speaker.industry = S['industry']
        if S['location'] or not speaker.location:
            speaker.location = S['location']
        bios = dict((b.language, b) for b in speaker.bios.all())
        speaker.save()
        for l in ('it', 'en'):
            try:
                b = bios[l]
            except KeyError:
                b = models.MultilingualContent()
                b.content_object = speaker
                b.language = l
                b.content = 'bios'
            if S['bio_' + l] or not b.body:
                b.body = S['bio_' + l]
            b.save()
    for tlk in tree.findall('talk'):
        T = {
            'title': tlk.find('title').text,
            'duration': int(tlk.find('duration').text),
            'language': 'en' if (tlk.find('language').text or '').startswith('en') else 'it',
            'tags': tlk.find('tags').text or '',
        }
        for ab in tlk.findall('abstract'):
            T['ab_' + ab.get('lang')] = ab.text or ''
        T['slug'] = slugify(T['title'])
        spk = slugify(tlk.find('speaker/name').text)
        speaker = models.Speaker.objects.get(slug = spk)
        try:
            talk = models.Talk.objects.get(slug = T['slug'])
        except models.Talk.DoesNotExist:
            talk = models.Talk()
            talk.title = T['title']
            talk.slug = T['slug']
        talk.duration = T['duration']
        talk.language = T['language']
        abstracts = dict((b.language, b) for b in talk.abstracts.all())
        talk.save()
        talk.speakers = [ speaker ]
        talk.save()
        for l in ('it', 'en'):
            try:
                b = abstracts[l]
            except KeyError:
                b = models.MultilingualContent()
                b.content_object = talk
                b.language = l
                b.content = 'abstracts'
            if T['ab_' + l] or not b.body:
                b.body = T['ab_' + l]
            b.save()
        
    request.user.message_set.create(message = 'talk importati')
    return HttpResponseRedirectSeeOther(request.META.get('HTTP_REFERER', '/'))

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

