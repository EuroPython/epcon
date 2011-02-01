# -*- coding: UTF-8 -*-
from __future__ import with_statement
import os.path
import urllib
import zipfile
import tempfile
from cStringIO import StringIO
from xml.etree import cElementTree as ET
from conference import models
from conference import settings
from conference.forms import SubmissionForm

from django.conf import settings as dsettings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import File
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify

import simplejson
from decorator import decorator

class HttpResponseRedirectSeeOther(HttpResponseRedirect):
    status_code = 303

def json(f):
    """
    decoratore da applicare ad una vista per serializzare in json il risultato.
    """
    if dsettings.DEBUG:
        ct = 'text/plain'
        j = lambda d: simplejson.dumps(d, indent = 2)
    else:
        ct = 'application/json'
        j = simplejson.dumps
    def wrapper(func, *args, **kw):
        try:
            result = func(*args, **kw)
        except Exception, e:
            result = j(str(e))
            status = 500
        else:
            if isinstance(result, HttpResponse):
                return result
            else:
                result = j(result)
                status = 200
        return HttpResponse(content = result, content_type = ct, status = status)
    return decorator(wrapper, f)

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
    conference = request.GET.getlist('conference')
    tags = request.GET.getlist('tag')
    return render_to_response(
        'conference/talk_report.html', {
            'conference': conference,
            'tags': tags,
        },
        context_instance = RequestContext(request))

@staff_member_required
@transaction.commit_on_success
def speaker_admin_image_upload(request):
    if request.method != 'POST':
        raise Http404()
    raw = []
    map(raw.append, request.FILES['zip'].chunks())
    zip = zipfile.ZipFile(StringIO(''.join(raw)), 'r')
    for name in zip.namelist():
        slug = slugify(os.path.splitext(name)[0])
        try:
            speaker = models.Speaker.objects.get(slug = slug)
        except models.Speaker.DoesNotExist:
            continue
        with tempfile.NamedTemporaryFile() as f:
            f.write(zip.read(name))
            f.seek(0)
            iname = os.path.join(slug, os.path.splitext(name)[1])
            speaker.image.save(iname, File(f))
    request.user.message_set.create(message = 'avatar aggiornati')
    return HttpResponseRedirectSeeOther(request.META.get('HTTP_REFERER', '/'))

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
            'conference': tlk.find('conference').text,
            'duration': int(tlk.find('duration').text),
            'language': 'en' if (tlk.find('language').text or '').startswith('en') else 'it',
            'tags': tlk.find('tags').text or '',
        }
        for ab in tlk.findall('abstract'):
            T['ab_' + ab.get('lang')] = ab.text or ''
        T['slug'] = slugify(T['title'])
        main_speakers = []
        additional_speakers = []
        for spk in tlk.findall('speaker'):
            if spk.get('type') == 'main':
                s = main_speakers
            else:
                s = additional_speakers
            slug = slugify(spk.find('name').text)
            s.append(models.Speaker.objects.get(slug = slug))
        try:
            talk = models.Talk.objects.get(slug = T['slug'])
        except models.Talk.DoesNotExist:
            talk = models.Talk()
            talk.title = T['title']
            talk.slug = T['slug']
            talk.conference = T['conference']
        talk.duration = T['duration']
        talk.language = T['language']
        abstracts = dict((b.language, b) for b in talk.abstracts.all())
        talk.save()
        talk.speakers = main_speakers
        talk.additional_speakers = additional_speakers
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

def schedule_xml(request, conference, slug):
    sch = get_object_or_404(models.Schedule, conference = conference, slug = slug)
    return render_to_response(
        'conference/schedule.xml', { 'schedule': sch },
        context_instance = RequestContext(request),
        mimetype = 'text/xml',
    )

def schedule_speakers_xml(request, conference, slug):
    sch = get_object_or_404(models.Schedule, conference = conference, slug = slug)
    query = Q(talk__event__schedule = sch) | Q(additional_speakers__event__schedule = sch)
    speakers = models.Speaker.objects.filter(query)
    return render_to_response(
        'conference/schedule_speakers.xml', { 'schedule': sch, 'speakers': speakers },
        context_instance = RequestContext(request),
        mimetype = 'text/xml',
    )

def talks_xml(request, conference):
    talks = models.Talk.objects.filter(conference=conference)
    return render_to_response(
        'conference/talks.xml', { 'conference': conference, 'talks': talks },
        context_instance = RequestContext(request),
        mimetype = 'text/xml',
    )

def genro_wrapper(request):
    """
    mostra in un iframe l'applicazione conference di genropy
    """
    try:
        conf = dict(dsettings.GNR_CONFERENCE)
    except AttributeError:
        raise Http404()
    conf['src'] += '?' + urllib.urlencode(request.GET)
    return render_to_response(
        'conference/genro_wrapper.html', conf,
        context_instance = RequestContext(request))

@json
def places(request):
    """
    ritorna un json special places ed hotel
    """
    places = []
    for h in models.SpecialPlace.objects.filter(visible = True):
        places.append({
            'id': h.id,
            'name': h.name,
            'address': h.address,
            'type': h.type,
            'url': h.url,
            'email': h.email,
            'telephone': h.telephone,
            'note': h.note,
            'lng': h.lng,
            'lat': h.lat,
            'html': render_to_string('conference/render_place.html', {'p': h}),
        })
    for h in models.Hotel.objects.filter(visible = True):
        places.append({
            'id': h.id,
            'name': h.name,
            'type': 'hotel',
            'telephone': h.telephone,
            'url': h.url,
            'email': h.email,
            'availability': h.availability,
            'price': h.price,
            'note': h.note,
            'affiliated': h.affiliated,
            'lng': h.lng,
            'lat': h.lat,
            'modified': h.modified.isoformat(),
            'html': render_to_string('conference/render_place.html', {'p': h}),
        })

    return places

@json
def sponsor(request, sponsor):
    """
    ritorna i dati dello sponsor richiesto
    """
    sponsor = get_object_or_404(models.Sponsor, slug = sponsor)
    return {
        'sponsor': sponsor.sponsor,
        'slug': sponsor.slug,
        'url': sponsor.url
    }


@login_required
@transaction.commit_on_success
def paper_submission(request):
    try:
        speaker = request.user.speaker
    except models.Speaker.DoesNotExist:
        speaker = None
    if request.method == 'POST':
        form = SubmissionForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            if speaker is None:
                name = '%s %s' % (request.user.first_name, request.user.last_name)
                speaker = models.Speaker.objects.createFromName(name, request.user)
            speaker.activity = data['activity']
            speaker.industry = data['industry']
            speaker.save()
            speaker.setBio(data['bio'])
            talk = models.Talk()
            talk.conference = settings.CONFERENCE
            talk.title = data['title']
            talk.slug = slugify(talk.title)
            talk.duration = data['duration']
            talk.language = data['language']
            talk.slides = data['slides']
            talk.status = 'proposed'
            talk.save()
            talk.speakers.add(speaker)
            talk.setAbstract(data['abstract'])
            messages.info(request, 'your talk has been submitted, thank you')
            return HttpResponseRedirectSeeOther(reverse('conference-speaker', kwargs={'slug': speaker.slug}))
    else:
        if speaker:
            data = {
                'activity': speaker.activity,
                'industry': speaker.industry,
                'bio': getattr(speaker.getBio(), 'body', ''),
            }
        else:
            data = {}
        form = SubmissionForm(initial=data)
    return render_to_response('conference/paper_submission.html', {
        'speaker': speaker,
        'form': form,
        'proposed_talks': speaker.talk_set.proposed(conference=settings.CONFERENCE) if speaker else [],
    }, context_instance=RequestContext(request))
