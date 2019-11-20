import os.path

from django import http
from django.conf import settings as dsettings

from django.contrib.auth.decorators import login_required
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
    return data

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


@profile_access
def user_profile(request, slug, profile=None, full_access=False):
    return redirect('profiles:profile', profile_slug=slug)


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
