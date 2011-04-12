# -*- coding: UTF-8 -*-
from __future__ import with_statement
import os.path
import tempfile
import urllib
import zipfile
from cStringIO import StringIO
from decimal import Decimal
from xml.etree import cElementTree as ET

from conference import models
from conference import settings
from conference.forms import SpeakerForm, SubmissionForm, TalkForm
from conference.utils import send_email

from django import forms
from django import http
from django.conf import settings as dsettings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import File
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify

import simplejson
from decorator import decorator

# see: http://www.djangosnippets.org/snippets/821/
def render_to(template):
    """
    Decorator for Django views that sends returned dict to render_to_response function
    with given template and RequestContext as context instance.

    If view doesn't return dict then decorator simply returns output.
    Additionally view can return two-tuple, which must contain dict as first
    element and string with template name as second. This string will
    override template name, given as parameter

    Parameters:

     - template: template name to use
    """
    def renderer(func):
        def wrapper(request, *args, **kw):
            output = func(request, *args, **kw)
            if isinstance(output, (list, tuple)):
                output, tpl = output
            else:
                tpl = template
            ct = 'text/html'
            if tpl.endswith('xml'):
                ct = 'text/xml' if dsettings.DEBUG else 'application/xml'
            if isinstance(output, dict):
                return render_to_response(tpl, output, RequestContext(request), mimetype=ct)
            else:
                return output
        return wrapper
    return renderer


class HttpResponseRedirectSeeOther(http.HttpResponseRedirect):
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
            if isinstance(result, http.HttpResponse):
                return result
            else:
                result = j(result)
                status = 200
        return http.HttpResponse(content = result, content_type = ct, status = status)
    return decorator(wrapper, f)

def speaker_access(f):
    """
    decoratore che protegge la view relativa ad uno speaker.
    """
    def wrapper(request, slug, **kwargs):
        spk = get_object_or_404(models.Speaker, slug=slug)
        if request.user.is_staff or request.user == spk.user:
            full_access = True
            talks = spk.talks()
        else:
            full_access = False
            conf = models.Conference.objects.current()
            if conf.voting():
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

@render_to('conference/speaker.html')
@speaker_access
def speaker(request, slug, speaker, talks, full_access):
    if request.method == 'GET':
        form = SpeakerForm(initial={
            'activity': speaker.activity,
            'activity_homepage': speaker.activity_homepage,
            'industry': speaker.industry,
            'company': speaker.company,
            'company_homepage': speaker.company_homepage,
            'bio': getattr(speaker.getBio(), 'body', ''),
        })
    elif request.method == 'POST':
        if not full_access:
            return http.HttpResponseBadRequest()
        form = SpeakerForm(data=request.POST)
        if form.is_valid():
            data = form.cleaned_data
            speaker.activity = data['activity']
            speaker.activity_homepage = data['activity_homepage']
            speaker.industry = data['industry']
            speaker.company = data['company']
            speaker.company_homepage = data['company_homepage']
            speaker.save()
            speaker.setBio(data['bio'])
            return HttpResponseRedirectSeeOther(reverse('conference-speaker', kwargs={'slug': speaker.slug}))
    return {
        'form': form,
        'full_access': full_access,
        'speaker': speaker,
        'talks': talks,
        'accepted': talks.filter(status='accepted'),
    }

@speaker_access
@render_to('conference/speaker.xml')
def speaker_xml(request, slug, speaker, full_access, talks):
    return {
        'speaker': speaker,
        'talks': talks,
    }

def talk_access(f):
    """
    decoratore che protegge la view relativa ad un talk.
    """
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
                # Il MultipleObjectsReturned può capitare se l'utente non è loggato
                # e .id vale None
                full_access = False
            else:
                full_access = True

        if tlk.status == 'proposed' and not full_access:
            conf = models.Conference.objects.current()
            if not conf.voting():
                raise http.Http404()
            if not settings.VOTING_ALLOWED(request.user):
                if settings.VOTING_DISALLOWED:
                    return redirect(settings.VOTING_DISALLOWED)
                else:
                    raise http.Http404()

        return f(request, slug, talk=tlk, full_access=full_access, **kwargs)
    return wrapper

@render_to('conference/talk.html')
@talk_access
def talk(request, slug, talk, full_access, talk_form=TalkForm):
    conf = models.Conference.objects.current()
    if request.method == 'GET':
        form = talk_form(initial={
            'title': talk.title,
            'training': talk.training_available,
            'duration': talk.duration,
            'language': talk.language,
            'level': talk.level,
            'abstract': talk.getAbstract().body,
        })
        form = talk_form(instance=talk)
    elif request.method == 'POST':
        if not full_access:
            return http.HttpResponseBadRequest()
        if conf.cfp():
            data = request.POST
        else:
            data = request.POST.copy()
            data['level'] = talk.level
            data['duration'] = talk.duration
            data['language'] = talk.language
        form = talk_form(data=data, files=request.FILES, instance=talk)
        if form.is_valid():
            talk = form.save()
            return HttpResponseRedirectSeeOther(reverse('conference-talk', kwargs={'slug': talk.slug}))
    return {
        'form': form,
        'full_access': full_access,
        'talk': talk,
        'cfp': conf.cfp(),
        'voting': conf.voting(),
    }

@render_to('conference/talk.xml')
@talk_access
def talk_xml(request, slug, talk, full_access):
    return {
        'talk': talk,
    }

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
        raise http.Http404()
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
        raise http.Http404()
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
        raise http.Http404()
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
def paper_submission(request, submission_form=SubmissionForm, submission_additional_form=TalkForm):
    try:
        speaker = request.user.speaker
    except models.Speaker.DoesNotExist:
        speaker = None

    conf = models.Conference.objects.current()
    if not conf.cfp_start or not conf.cfp_end:
        raise http.Http404()

    if not conf.cfp():
        if settings.CFP_CLOSED:
            return redirect(settings.CFP_CLOSED)
        else:
            raise http.Http404()

    proposed = speaker.talk_set.proposed(conference=settings.CONFERENCE) if speaker else []
    if request.method == 'POST':
        if len(proposed) == 0:
            form = submission_form(user=request.user, data=request.POST, files=request.FILES)
        else:
            form = submission_additional_form(data=request.POST, files=request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            if len(proposed) == 0:
                talk = form.save()
                speaker = request.user.speaker
            else:
                talk = form.save(speaker=speaker)
            messages.info(request, 'Your talk has been submitted, thank you!')
            send_email(
                subject='[new paper] "%s %s" - %s' % (request.user.first_name, request.user.last_name, data['title']),
                message='Title: %s\nDuration: %s\nLanguage: %s\nAlso training: %s\n\nAbstract: %s' % (data['title'], data['duration'], data['language'], data['training'], data['abstract']),
            )
            return HttpResponseRedirectSeeOther(reverse('conference-speaker', kwargs={'slug': speaker.slug}))
    else:
        if len(proposed) == 0:
            form = submission_form(user=request.user)
        else:
            form = submission_additional_form()
    return render_to_response('conference/paper_submission.html', {
        'speaker': speaker,
        'form': form,
        'proposed_talks': proposed,
    }, context_instance=RequestContext(request))

@render_to('conference/voting.html')
def voting(request):
    conf = models.Conference.objects.current()

    if not conf.voting():
        if settings.VOTING_CLOSED:
            return redirect(settings.VOTING_CLOSED)
        else:
            raise http.Http404()

    voting_allowed = settings.VOTING_ALLOWED(request.user)

    talks = models.Talk.objects\
                .proposed(conference=conf.code)

    if request.method == 'POST':
        if not voting_allowed:
            return http.HttpResponseBadRequest('anonymous user not allowed')

        data = dict((x.id, x) for x in talks)
        for k, v in filter(lambda x: x[0].startswith('vote-'), request.POST.items()):
            try:
                talk = data[int(k[5:])]
            except KeyError:
                return http.HttpResponseBadRequest('invalid talk')
            except ValueError:
                return http.HttpResponseBadRequest('id malformed')
            if not v:
                models.VotoTalk.objects.filter(user=request.user, talk=talk).delete()
                talks.user_vote = None
            else:
                try:
                    vote = Decimal(v)
                except ValueError:
                    return http.HttpResponseBadRequest('vote malformed')
                try:
                    o = models.VotoTalk.objects.get(user=request.user, talk=talk)
                except models.VotoTalk.DoesNotExist:
                    o = models.VotoTalk(user=request.user, talk=talk)
                o.vote = vote
                o.save()
                talks.user_vote = o
        if request.is_ajax():
            return http.HttpResponse('')
        else:
            return HttpResponseRedirectSeeOther(reverse('conference-voting') + '?' + request.GET.urlencode())
    else:
        class OptionForm(forms.Form):
            abstracts = forms.ChoiceField(
                choices=(('not-voted', 'To be voted'), ('all', 'All'),),
                required=False,
            )
            talk_type = forms.ChoiceField(
                choices=(('all', 'All'), ('talk', 'Talks'), ('training', 'Trainings'),),
                required=False,
            )
            language = forms.ChoiceField(
                choices=(('all', 'All'), ('en', 'English'), ('it', 'Italian'),),
                required=False,
            )
            order = forms.ChoiceField(
                choices=(('vote', 'Vote'), ('speaker', 'Speaker name'),),
                required=False,
            )

        form = OptionForm(data=request.GET)

        user_votes = models.VotoTalk.objects.filter(user=request.user.id)
        talks = talks.order_by('speakers__name')

        form.is_valid()
        options = form.cleaned_data
        if options['abstracts'] != 'all':
            talks = talks.exclude(id__in=user_votes.values('talk_id'))
        if options['talk_type'] == 'talk':
            talks = talks.filter(training_available=False)
        elif options['talk_type'] == 'training':
            talks = talks.filter(training_available=True)

        if options['language'] == 'en':
            talks = talks.filter(language='en')
        elif options['language'] == 'it':
            talks = talks.filter(language='it')

        votes = dict((x.talk_id, x) for x in user_votes)

        # Poichè talks è ordinato per un modello collegato tramite una
        # ManyToMany posso avere dei talk ripetuti, purtroppo per un limite di
        # django la .distinct() non funziona perché l'orm aggiunge alle colonne
        # della select anche il campo per cui si ordina.
        #
        # Non mi rimane che filtrare in python, a questo punto ne approfitto
        # per agganciare i voti dell'utente utilizzando un unico loop.
        dups = set()
        def filter_vote(t):
            if t.id in dups:
                return False
            dups.add(t.id)
            t.user_vote = votes.get(t.id)
            return True
        talks = filter(filter_vote, talks)

        if options['order'] != 'speaker':
            def key(x):
                if x.user_vote:
                    return x.user_vote.vote
                else:
                    return Decimal('-99.99')
            talks = reversed(sorted(reversed(talks), key=key))

        return {
            'voting_allowed': voting_allowed,
            'talks': talks,
            'form': form,
        }
