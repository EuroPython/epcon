import os.path
import random
from datetime import date
from decimal import Decimal

from django import forms, http
from django.conf import settings as dsettings

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect, render, render_to_response
from django.template.response import TemplateResponse

from common.decorators import render_to_json
from common.decorators import render_to_template
from conference import dataaccess, models, settings, utils
from conference.decorators import speaker_access, talk_access, profile_access
from conference.forms import AttendeeLinkDescriptionForm, SpeakerForm, TalkForm


class HttpResponseRedirectSeeOther(http.HttpResponseRedirect):
    status_code = 303


@speaker_access
@render_to_template('conference/speaker.html')
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
@render_to_template('conference/speaker.xml')
def speaker_xml(request, slug, speaker, full_access, talks):
    return {
        'speaker': speaker,
        'talks': talks,
    }


def talk(request, slug):
    return redirect('talks:talk', permanent=True, talk_slug=slug)


@render_to_template('conference/talk_preview.html')
@talk_access
def talk_preview(request, slug, talk, full_access, talk_form=TalkForm):
    conf = models.Conference.objects.current()
    return {
        'talk': talk,
        'voting': conf.voting(),
    }


@talk_access
def talk_xml(request, slug, talk, full_access):
    return TemplateResponse(
        request,
        'conference/talk.xml',
        {'talk': talk},
        content_type='application/xml'
    )


def talk_video(request, slug):  # pragma: no cover
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
        r = http.HttpResponse(file(vfile), content_type=mt)
    elif settings.X_SENDFILE['type'] == 'x-accel':
        r = http.HttpResponse('', content_type=mt)
        r['X-Accel-Redirect'] = vurl
    elif settings.X_SENDFILE['type'] == 'custom':
        return settings.X_SENDFILE['f'](tlk, url=vurl, fpath=vfile, content_type=mt)
    else:
        raise RuntimeError('invalid X_SENDFILE')
    fname = '%s%s' % (tlk.title.encode('utf-8'), vext.encode('utf-8'))
    r['content-disposition'] = 'attachment; filename="%s"' % fname
    return r


@render_to_template('conference/conference.xml')
def conference_xml(request, conference):
    conference = get_object_or_404(models.Conference, code=conference)
    talks = models.Talk.objects.filter(conference=conference)
    schedules = [
        (s, utils.TimeTable2.fromSchedule(s.id))
        for s in models.Schedule.objects.filter(conference=conference.code)
    ]
    return {
        'conference': conference,
        'talks': talks,
        'schedules': schedules,
    }


def talk_report(request):  # pragma: no cover
    conference = request.GET.getlist('conference')
    tags = request.GET.getlist('tag')
    return render_to_response(
        'conference/talk_report.html', {
            'conference': conference,
            'tags': tags,
        },
    )


@render_to_template('conference/schedule.html')
def schedule(request, conference, slug):
    sch = get_object_or_404(models.Schedule, conference=conference, slug=slug)
    return {
        'schedule': sch,
    }


@login_required
@render_to_json
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
@render_to_json
def schedule_event_booking(request, conference, slug, eid):
    evt = get_object_or_404(models.Event, schedule__conference=conference, schedule__slug=slug, id=eid)
    status = models.EventBooking.objects.booking_status(evt.id)
    if request.method == 'POST':
        fc = utils.dotted_import(settings.FORMS['EventBooking'])
        form = fc(event=evt.id, user=request.user.id, data=request.POST)
        if form.is_valid():
            if form.cleaned_data['value']:
                models.EventBooking.objects.book_event(evt.id, request.user.id)
                if request.user.id not in status['booked']:
                    status['booked'].append(request.user.id)
            else:
                models.EventBooking.objects.cancel_reservation(evt.id, request.user.id)
                try:
                    status['booked'].remove(request.user.id)
                except ValueError:
                    pass
        else:
            try:
                msg = str(form.errors['value'][0])
            except:
                msg = ""
            return http.HttpResponseBadRequest(msg)
    return {
        'booked': len(status['booked']),
        'available': max(status['available'], 0),
        'seats': status['seats'],
        'user': request.user.id in status['booked'],
    }


@render_to_json
def schedule_events_booking_status(request, conference):
    data = dataaccess.conference_booking_status(conference)
    uid = request.user.id if request.user.is_authenticated else 0
    for k, v in data.items():
        if uid and uid in v['booked']:
            v['user'] = True
        else:
            v['user'] = False
        del v['booked']
    return dat
    a

@render_to_template('conference/schedule.xml')
def schedule_xml(request, conference, slug):
    sch = get_object_or_404(models.Schedule, conference=conference, slug=slug)
    return {
        'schedule': sch,
        'timetable': utils.TimeTable2.fromSchedule(sch.id),
    }


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


@login_required
#@transaction.atomic
def paper_submission(request):
    try:
        speaker = request.user.speaker
    except models.Speaker.DoesNotExist:
        speaker = None

    conf = models.Conference.objects.current()

    if not conf.cfp_start or not conf.cfp_end:
        return TemplateResponse(request,
                                "conference/cfp/unkown_cfp_status.html")

    if date.today() < conf.cfp_start:
        return TemplateResponse(request,
                                "conference/cfp/cfp_not_started.html")

    if date.today() > conf.cfp_end:
        return TemplateResponse(request,
                                "conference/cfp/cfp_already_closed.html")


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
            return redirect(reverse('cfp-thank-you-for-proposal'))
    else:
        if not proposed:
            form = fc(user=request.user)
        else:
            form = fc()

    return render(request, 'conference/paper_submission.html', {
        'speaker': speaker,
        'form': form,
        'proposed_talks': proposed,
    })


def cfp_thank_you_for_proposal(request):
    return TemplateResponse(
        request, "conference/cfp/thank_you_for_proposal.html"
    )


def get_data_for_context(request):
    conf = models.Conference.objects.current()
    voting_allowed = settings.VOTING_ALLOWED(request.user)
    talks = models.Talk.objects.proposed(conference=conf.code)
    return conf, talks, voting_allowed


def voting(request):

    conf, talks, voting_allowed = get_data_for_context(request)

    if not settings.VOTING_OPENED(conf, request.user):
        if settings.VOTING_CLOSED:
            return redirect(settings.VOTING_CLOSED)
        else:
            raise http.Http404()

    if request.method == 'POST':
        if not voting_allowed:
            return http.HttpResponseBadRequest('anonymous user not allowed')

        data = dict((x.id, x) for x in talks)
        for k, v in [x for x in request.POST.items() if x[0].startswith('vote-')]:
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
        from conference.forms import TagField, ReadonlyTagWidget, PseudoRadioSelectWidget
        class OptionForm(forms.Form):
            abstracts = forms.ChoiceField(
                choices=(('not-voted', 'Not yet voted'),
                         ('all', 'All'),
                         ),
                required=False,
                initial='not-voted',
                widget=PseudoRadioSelectWidget(),
            )
            talk_type = forms.ChoiceField(
                label='Session type',
                choices=(('all', 'All'),) + tuple(settings.TALK_TYPES_TO_BE_VOTED),
                required=False,
                initial='all',
                widget=PseudoRadioSelectWidget(),
            )
            language = forms.ChoiceField(
                choices=(('all', 'All'),) + tuple(settings.TALK_SUBMISSION_LANGUAGES),
                required=False,
                initial='all',
                widget=PseudoRadioSelectWidget(),
            )
            order = forms.ChoiceField(
                choices=(('random', 'Random order'),
                         ('vote', 'Vote'),
                         ('speaker', 'Speaker name'),
                         ),
                required=False,
                initial='random',
                widget=PseudoRadioSelectWidget(),
            )
            tags = TagField(
                required=False,
                widget=ReadonlyTagWidget(),
            )

        # I want to associate with each talk a "unique" number to display next to the title to be able to easily find.
        ordinal = dict()
        for ix, t in enumerate(talks.order_by('created').values_list('id', flat=True)):
            ordinal[t] = ix

        user_votes = models.VotoTalk.objects.filter(user=request.user.id)

        # Start by sorting talks by name
        talks = talks.order_by('speakers__user__first_name',
                               'speakers__user__last_name')

        if request.GET:
            form = OptionForm(data=request.GET)
            form.is_valid()
            options = form.cleaned_data
        else:
            form = OptionForm()
            options = {
                'abstracts': 'not-voted',
                'talk_type': 'all',
                'language': 'all',
                'tags': '',
                'order': 'random',
            }
        # if options['abstracts'] == 'not-voted':
        #     talks = talks.exclude(id__in=user_votes.values('talk_id'))
        if options['talk_type'] in (tchar
                                    for (tchar, tdef) in settings.TALK_TYPES_TO_BE_VOTED):
            talks = talks.filter(type__startswith=options['talk_type'])

        if options['language'] in (lcode
                                   for (lcode, ldef) in settings.TALK_SUBMISSION_LANGUAGES):
            talks = talks.filter(language=options['language'])

        if options['tags']:
            # if options['tags'] ends us a tag not associated with any talk I results
            # in a query that results from scratch; to avoid this limit the usable tag
            # as a filter to those associated with talk.
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

        # As talks are sorted by a model connected via a m2m can I have repeated the talk, and
        # distinct does not apply in these case.
        #
        # It can only filtered in python, at this point I take this opportunity to engage
        # votes user using a single loop.
        dups = set()
        def filter_vote(t):
            if t['id'] in dups:
                return False
            dups.add(t['id'])
            t['user_vote'] = votes.get(t['id'])
            t['ordinal'] = ordinal[t['id']]
            return True
        talks = list(filter(filter_vote, talks.values('id')))

        # Fix talk order, if necessary
        if talk_order == 'vote':
            def key(x):
                if x['user_vote']:
                    return x['user_vote'].vote
                else:
                    return Decimal('-99.99')
            talks = reversed(sorted(reversed(talks), key=key))
        elif talk_order == 'random':
            random.shuffle(talks)
        elif talk_order == 'speaker':
            # Already sorted
            pass

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


@render_to_template('conference/profile.html')
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


@render_to_json
def schedule_events_expected_attendance(request, conference):
    return dataaccess.expected_attendance(conference)


def covers(request, conference):
    events = settings.VIDEO_COVER_EVENTS(conference)
    if not events:
        raise http.Http404()

    schedules = dataaccess.schedules_data(
        models.Schedule.objects\
            .filter(conference=conference)\
            .order_by('date')\
            .values_list('id', flat=True)
    )

    from collections import defaultdict
    tracks = defaultdict(dict)
    for s in schedules:
        for t in s['tracks'].values():
            tracks[s['id']][t.track] = t.title

    grouped = defaultdict(lambda: defaultdict(list))
    for e in dataaccess.events(eids=events):
        if not e['tracks']:
            continue
        sid = e['schedule_id']
        t = tracks[sid][e['tracks'][0]]
        grouped[sid][t].append(e)

    ordered = []
    for s in schedules:
        data = grouped[s['id']]
        if not data:
            continue
        ordered.append((s, sorted(data.items())))
    ctx = {
        'conference': conference,
        'events': ordered,
    }
    return render(request, 'conference/covers.html', ctx)


@login_required
def user_profile_link(request, uuid):
    """
    """
    profile = get_object_or_404(models.AttendeeProfile, uuid=uuid).user_id
    conf = models.Conference.objects.current()
    active = conf.conference() or 1
    if request.user.id == profile:
        if active:
            p, _ = models.Presence.objects.get_or_create(profile_id=profile, conference=conf.code)
        return redirect('conference-myself-profile')

    uid = request.user.id
    created = linked = False
    try:
        link = models.AttendeeLink.objects.getLink(uid, profile)
        linked = True
    except models.AttendeeLink.DoesNotExist:
        if active:
            link = models.AttendeeLink(attendee1_id=uid, attendee2_id=profile)
            link.save()

            from conference.signals import attendees_connected
            attendees_connected.send(link, attendee1=uid, attendee2=profile)

            created = True
            linked = True
    form = AttendeeLinkDescriptionForm(initial={
        'message': link.message,
    })
    ctx = {
        'profile2': profile,
        'created': created,
        'linked': linked,
        'form': form,
    }
    return render(request, 'conference/profile_link.html', ctx)


@login_required
@render_to_json
def user_profile_link_message(request, uuid):
    profile = get_object_or_404(models.AttendeeProfile, uuid=uuid).user_id
    uid = request.user.id
    if uid == profile:
        return {}

    try:
        link = models.AttendeeLink.objects.getLink(uid, profile)
    except models.AttendeeLink.DoesNotExist:
        raise http.Http404()

    if request.method == 'POST':
        form = AttendeeLinkDescriptionForm(data=request.POST)
        if form.is_valid():
            link.message = form.cleaned_data['message']
            link.save()
    return {}


@login_required
def user_conferences(request):
    uid = request.user.id
    conferences = models.Conference.objects.filter(
        code__in=models.Presence.objects.filter(profile=uid).values('conference'))
    people = []
    for p in models.AttendeeLink.objects.findLinks(uid).order_by('timestamp'):
        if p.attendee1_id == uid:
            p.other = p.attendee2_id
        else:
            p.other = p.attendee1_id
        people.append(p)
    ctx = {
        'conferences': conferences,
        'people': people,
    }
    return render(request, 'conference/user_conferences.html', ctx)
