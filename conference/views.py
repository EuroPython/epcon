# -*- coding: UTF-8 -*-
from __future__ import with_statement
import functools
import os.path
import urllib
from collections import defaultdict
from decimal import Decimal

from conference import dataaccess
from conference import models
from conference import settings
from conference import utils
from conference.forms import SpeakerForm, TalkForm

from django import forms
from django import http
from django.conf import settings as dsettings
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render_to_response, get_object_or_404, render
from django.template import RequestContext
from django.template.loader import render_to_string

import simplejson
from decorator import decorator

class MyEncode(simplejson.JSONEncoder):
    def default(self, obj):
        import datetime, decimal
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%d/%m/%Y %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%d/%m/%Y')
        elif isinstance(obj, datetime.time):
            return obj.strftime('%H:%M')
        elif isinstance(obj, decimal.Decimal):
            return str(obj)
        elif isinstance(obj, set):
            return list(obj)

        return simplejson.JSONEncoder.default(self, obj)

json_dumps = functools.partial(simplejson.dumps, cls=MyEncode)

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
                if request.is_ajax() and settings.TEMPLATE_FOR_AJAX_REQUEST:
                    tpl = ('%s_body%s' % os.path.splitext(tpl), tpl)
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

@render_to('conference/speaker.html')
@speaker_access
def speaker(request, slug, speaker, talks, full_access, speaker_form=SpeakerForm):
    if request.method == 'POST':
        if not full_access:
            return http.HttpResponseBadRequest()
        form = speaker_form(data=request.POST)
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
    else:
        form = speaker_form(initial={
            'activity': speaker.activity,
            'activity_homepage': speaker.activity_homepage,
            'industry': speaker.industry,
            'company': speaker.company,
            'company_homepage': speaker.company_homepage,
            'bio': getattr(speaker.getBio(), 'body', ''),
        })
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

        # Se il talk non è confermato possono accedere:
        #   * i super user o gli speaker (full_access = True)
        #   * se la votazione comunitarià è in corso chi ha il diritto di votare
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

@render_to('conference/talk.html')
@talk_access
def talk(request, slug, talk, full_access, talk_form=None):
    conf = models.Conference.objects.current()
    if talk_form is None:
        talk_form = utils.dotted_import(settings.FORMS['AdditionalPaperSubmission'])
    if request.method == 'POST':
        if not full_access:
            return http.HttpResponseBadRequest()
        if conf.cfp():
            data = request.POST
        else:
            data = request.POST.copy()
            data['level'] = talk.level
            data['duration'] = talk.duration
            data['language'] = talk.language
            data['type'] = talk.type
            data['tags'] = ','.join([ x.name for x in talk.tags.all() ])
        form = talk_form(data=data, files=request.FILES, instance=talk)
        if form.is_valid():
            talk = form.save()
            messages.info(request, 'Your talk has been modified.')
            return HttpResponseRedirectSeeOther(reverse('conference-talk', kwargs={'slug': talk.slug}))
    else:
        form = talk_form(instance=talk)
    return {
        'form': form,
        'full_access': full_access,
        'talk': talk,
        'cfp': conf.cfp(),
        'voting': conf.voting(),
    }

@render_to('conference/talk_preview.html')
@talk_access
def talk_preview(request, slug, talk, full_access, talk_form=TalkForm):
    conf = models.Conference.objects.current()
    return {
        'talk': talk,
        'voting': conf.voting(),
    }

@render_to('conference/talk.xml')
@talk_access
def talk_xml(request, slug, talk, full_access):
    return {
        'talk': talk,
    }

def talk_video(request, slug):
    tlk = get_object_or_404(models.Talk, slug=slug)

    if not tlk.video_type or tlk.video_type == 'download':
        if tlk.video_file:
            vurl = dsettings.MEDIA_URL + tlk.video_file.url
            vfile = tlk.video_file.path
        elif settings.VIDEO_DOWNLOAD_FALLBACK:
            for ext in ('.avi', '.mp4'):
                fpath = os.path.join(dsettings.MEDIA_ROOT, 'conference/videos', tlk.slug + ext)
                if os.path.exists(fpath):
                    vurl = dsettings.MEDIA_URL + 'conference/videos/' + tlk.slug + ext
                    vfile = fpath
                    break
            else:
                raise http.Http404()
        else:
            raise http.Http404()
    else:
        raise http.Http404()

    if settings.TALK_VIDEO_ACCESS:
        if not settings.TALK_VIDEO_ACCESS(request, tlk):
            return http.HttpResponseForbidden()

    vext = os.path.splitext(vfile)[1]
    if vext == '.mp4':
        mt = 'video/mp4'
    elif vext == '.avi':
        mt = 'video/x-msvideo'
    else:
        mt = None
    if settings.X_SENDFILE is None:
        r = http.HttpResponse(file(vfile), mimetype=mt)
    elif settings.X_SENDFILE['type'] == 'x-accel':
        r = http.HttpResponse('', mimetype=mt)
        r['X-Accel-Redirect'] = vurl
    elif settings.X_SENDFILE['type'] == 'custom':
        return settings.X_SENDFILE['f'](tlk, url=vurl, fpath=vfile, mimetype=mt)
    else:
        raise RuntimeError('invalid X_SENDFILE')
    fname = '%s%s' % (tlk.title.encode('utf-8'), vext.encode('utf-8'))
    r['content-disposition'] = 'attachment; filename="%s"' % fname
    return r

@render_to('conference/conference.xml')
def conference_xml(request, conference):
    conference = get_object_or_404(models.Conference, code=conference)
    talks = models.Talk.objects.filter(conference=conference)
    schedules = models.Schedule.objects.filter(conference=conference.code)
    return {
        'conference': conference,
        'talks': talks,
        'schedules': schedules,
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

@render_to('conference/schedule.html')
def schedule(request, conference, slug):
    sch = get_object_or_404(models.Schedule, conference=conference, slug=slug)
    return {
        'schedule': sch,
    }

@login_required
@json
def schedule_event_interest(request, conference, slug, eid):
    evt = get_object_or_404(models.Event, schedule__conference=conference, schedule__slug=slug, id=eid)
    if request.method == 'POST':
        val = int(request.POST['interest'])
        try:
            ei = evt.eventinterest_set.get(user=request.user)
        except models.EventInterest.DoesNotExist:
            ei = None
        if val == 0 and ei:
            ei.delete()
        elif val != 0:
            if not ei:
                ei = models.EventInterest(event=evt, user=request.user)
            ei.interest = val
            ei.save()
    else:
        try:
            val = evt.eventinterest_set.get(user=request.user).interest
        except models.EventInterest.DoesNotExist:
            val = 0
    return { 'interest': val }

@login_required
@json
def schedule_event_booking(request, conference, slug, eid):
    evt = get_object_or_404(models.Event, schedule__conference=conference, schedule__slug=slug, id=eid)
    status = models.EventBooking.objects.booking_status(evt.id)
    if request.method == 'POST':
        fc = utils.dotted_import(settings.FORMS['EventBooking'])
        form = fc(event=evt.id, user=request.user.id, data=request.POST)
        if form.is_valid():
            if form.cleaned_data['value']:
                models.EventBooking.objects.book_event(evt.id, request.user.id)
                status['booked'].append(request.user.id)
            else:
                models.EventBooking.objects.cancel_reservation(evt.id, request.user.id)
                status['booked'].remove(request.user.id)
        else:
            try:
                msg = unicode(form.errors['value'][0])
            except:
                msg = ""
            return http.HttpResponseBadRequest(msg)
    return {
        'booked': len(status['booked']),
        'available': max(status['available'], 0),
        'seats': status['seats'],
        'user': request.user.id in status['booked'],
    }

@json
def schedule_events_booking_status(request, conference):
    data = dataaccess.conference_booking_status(conference)
    uid = request.user.id if request.user.is_authenticated() else 0
    for k, v in data.items():
        if uid and uid in v['booked']:
            v['user'] = True
        else:
            v['user'] = False
        del v['booked']
    return data

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
def paper_submission(request):
    try:
        speaker = request.user.speaker
    except models.Speaker.DoesNotExist:
        speaker = None

    conf = models.Conference.objects.current()

    # per questa conferenza non è previsto il cfp
    if not conf.cfp_start or not conf.cfp_end:
        raise http.Http404()

    # il cfp è concluso
    if not conf.cfp():
        if settings.CFP_CLOSED:
            return redirect(settings.CFP_CLOSED)
        else:
            raise http.Http404()

    if speaker:
        proposed = list(speaker.talk_set.proposed(conference=settings.CONFERENCE))
    else:
        proposed = []
    if not proposed:
        fc = utils.dotted_import(settings.FORMS['PaperSubmission'])
        form = fc(user=request.user, data=request.POST, files=request.FILES)
    else:
        fc = utils.dotted_import(settings.FORMS['AdditionalPaperSubmission'])
        form = fc(data=request.POST, files=request.FILES)

    if request.method == 'POST':
        if not proposed:
            form = fc(user=request.user, data=request.POST, files=request.FILES)
        else:
            form = fc(data=request.POST, files=request.FILES)

        if form.is_valid():
            if not proposed:
                talk = form.save()
                speaker = request.user.speaker
            else:
                talk = form.save(speaker=speaker)
            messages.info(request, 'Your talk has been submitted, thank you!')
            return HttpResponseRedirectSeeOther(reverse('conference-myself-profile'))
    else:
        if not proposed:
            form = fc(user=request.user)
        else:
            form = fc()
    return render_to_response('conference/paper_submission.html', {
        'speaker': speaker,
        'form': form,
        'proposed_talks': proposed,
    }, context_instance=RequestContext(request))

def voting(request):
    conf = models.Conference.objects.current()

    if not settings.VOTING_OPENED(conf, request.user):
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
            else:
                try:
                    vote = Decimal(v)
                except ValueError:
                    return http.HttpResponseBadRequest('vote malformed')
                try:
                    o = models.VotoTalk.objects.get(user=request.user, talk=talk)
                except models.VotoTalk.DoesNotExist:
                    o = models.VotoTalk(user=request.user, talk=talk)
                if not vote:
                    if o.id:
                        o.delete()
                else:
                    o.vote = vote
                    o.save()
        if request.is_ajax():
            return http.HttpResponse('')
        else:
            return HttpResponseRedirectSeeOther(reverse('conference-voting') + '?' + request.GET.urlencode())
    else:
        from conference.forms import TagField, ReadonlyTagWidget, PseudoRadioRenderer
        class OptionForm(forms.Form):
            abstracts = forms.ChoiceField(
                choices=(('not-voted', 'To be voted'), ('all', 'All'),),
                required=False,
                initial='not-voted',
                widget=forms.RadioSelect(renderer=PseudoRadioRenderer),
            )
            talk_type = forms.ChoiceField(
                choices=(('all', 'All'), ('s', 'Talks'), ('t', 'Trainings'), ('p', 'Poster'),),
                required=False,
                initial='all',
                widget=forms.RadioSelect(renderer=PseudoRadioRenderer),
            )
            language = forms.ChoiceField(
                choices=(('all', 'All'), ('en', 'English'), ('it', 'Italian'),),
                required=False,
                initial='all',
                widget=forms.RadioSelect(renderer=PseudoRadioRenderer),
            )
            order = forms.ChoiceField(
                choices=(('vote', 'Vote'), ('speaker', 'Speaker name'),),
                required=False,
                initial='vote',
                widget=forms.RadioSelect(renderer=PseudoRadioRenderer),
            )
            tags = TagField(
                required=False,
                widget=ReadonlyTagWidget(),
            )

        # voglio poter associare ad ogni talk un numero "univoco" da mostrare
        # accanto al titolo per poterlo individuare facilmente.
        ordinal = dict()
        for ix, t in enumerate(talks.order_by('created').values_list('id', flat=True)):
            ordinal[t] = ix

        user_votes = models.VotoTalk.objects.filter(user=request.user.id)
        talks = talks.order_by('speakers__user__first_name', 'speakers__user__last_name')

        if request.GET:
            form = OptionForm(data=request.GET)
            form.is_valid()
            options = form.cleaned_data
        else:
            form = OptionForm()
            options = {
                'abstracts': 'not-voted',
                'talk_type': '',
                'language': '',
                'tags': '',
                'order': 'vote',
            }
        if options['abstracts'] != 'all':
            talks = talks.exclude(id__in=user_votes.values('talk_id'))
        if options['talk_type'] in ('s', 't', 'p'):
            talks = talks.filter(type=options['talk_type'])

        if options['language'] in ('en', 'it'):
            talks = talks.filter(language=options['language'])

        if options['tags']:
            # se in options['tags'] ci finisce un tag non associato ad alcun
            # talk ho come risultato una query che da zero risultati; per
            # evitare questo limito i tag usabili come filtro a quelli
            # associati ai talk.
            allowed = set()
            ctt = ContentType.objects.get_for_model(models.Talk)
            for t, usage in dataaccess.tags().items():
                for cid, oid in usage:
                    if cid == ctt.id:
                        allowed.add(t.name)
                        break
            tags = set(options['tags']) & allowed
            if tags:
                talks = talks.filter(id__in=models.ConferenceTaggedItem.objects\
                    .filter(
                        content_type__app_label='conference', content_type__model='talk',
                        tag__name__in=tags)\
                    .values('object_id')
                )

        talk_order = options['order']

        votes = dict((x.talk_id, x) for x in user_votes)

        # Poichè talks è ordinato per un modello collegato tramite una
        # ManyToMany posso avere dei talk ripetuti, e il distinct non si
        # applica in questi casi.
        #
        # Non mi rimane che filtrare in python, a questo punto ne approfitto
        # per agganciare i voti dell'utente utilizzando un unico loop.
        dups = set()
        def filter_vote(t):
            if t['id'] in dups:
                return False
            dups.add(t['id'])
            t['user_vote'] = votes.get(t['id'])
            t['ordinal'] = ordinal[t['id']]
            return True
        talks = filter(filter_vote, talks.values('id'))

        if talk_order != 'speaker':
            def key(x):
                if x['user_vote']:
                    return x['user_vote'].vote
                else:
                    return Decimal('-99.99')
            talks = reversed(sorted(reversed(talks), key=key))

        ctx = {
            'voting_allowed': voting_allowed,
            'talks': list(talks),
            'form': form,
        }
        if request.is_ajax():
            tpl = 'conference/ajax/voting.html'
        else:
            tpl = 'conference/voting.html'
        return render(request, tpl, ctx)

def profile_access(f):
    """
    decoratore che protegge la view relativa ad un profilo.
    """
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
            # se il profilo appartiene ad uno speaker con dei talk "accepted" è
            # visibile qualunque cosa dica il profilo stesso
            accepted = models.TalkSpeaker.objects\
                .filter(speaker__user=profile.user)\
                .filter(talk__status='accepted')\
                .count()
            if not accepted:
                # Se la votazione comunitaria à aperta e il profilo appartiene
                # ad uno speaker con dei talk in gara la pagina è visibile
                conf = models.Conference.objects.current()
                if not (settings.VOTING_OPENED(conf, request.user) and settings.VOTING_ALLOWED(request.user)):
                    if profile.visibility == 'x':
                        return http.HttpResponseForbidden()
                    elif profile.visibility == 'm' and request.user.is_anonymous:
                        return http.HttpResponseForbidden()
        return f(request, slug, profile=profile, full_access=full_access, **kwargs)
    return wrapper

@render_to('conference/profile.html')
@profile_access
def user_profile(request, slug, profile=None, full_access=False):
    fc = utils.dotted_import(settings.FORMS['Profile'])
    if request.method == 'POST':
        if not full_access:
            return http.HttpResponseForbidden()
        form = fc(instance=profile, data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirectSeeOther(reverse('conference-profile', kwargs={'slug': profile.slug}))
    else:
        if full_access:
            form = fc(instance=profile)
        else:
            form = None
    return {
        'form': form,
        'full_access': full_access,
        'profile': profile,
    }

@login_required
def myself_profile(request):
    p = models.AttendeeProfile.objects.getOrCreateForUser(request.user)
    return redirect('conference-profile', slug=p.slug)
