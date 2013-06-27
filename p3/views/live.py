# -*- coding: UTF-8 -*-
import datetime
from assopy.views import render_to_json
from conference import models as cmodels
from conference.utils import TimeTable2
from django import http
from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import render
from p3 import dataaccess

def _live_conference():
    conf = cmodels.Conference.objects.current()
    if not conf.conference():
        if not settings.DEBUG:
            raise http.Http404()
        else:
            wday = datetime.date.today().weekday()
            date = conf.conference_start
            while date <= conf.conference_end:
                if date.weekday() == wday:
                    break
                date = date + datetime.timedelta(days=1)
    else:
        date = datetime.date.today()
    return conf, date

def live(request):
    """
    What's up doc?
    """
    conf, date = _live_conference()

    tracks = cmodels.Track.objects\
        .filter(track__in=settings.P3_LIVE_TRACKS.keys(), schedule__date=date)\
        .order_by('order')

    ctx = {
        'tracks': tracks,
    }
    return render(request, 'p3/live.html', ctx)

def live_track(request, track):
    return render(request, 'p3/live_track.html', {})

def live_track_video(request, track):
    url = settings.P3_LIVE_REDIRECT_URL(request, track)
    class R(http.HttpResponseRedirect):
        allowed_schemes = ['http', 'https', 'rtsp', 'rtmp']
    return R(url)

@render_to_json
def live_track_events(request, track):
    conf, date = _live_conference()

    tid = cmodels.Track.objects\
        .get(track=track, schedule__date=date).id
    tt = TimeTable2.fromTracks([tid])
    output = []
    for _, events in tt.iterOnTracks():
        for e in events:
            if e.get('talk'):
                speakers = ', '.join([ x['name'] for x in e['talk']['speakers']])
            else:
                speakers = None
            output.append({
                'name': e['name'],
                'time': e['time'],
                'duration': e['duration'],
                'tags': e['tags'],
                'speakers': speakers,
            })
    return output

@render_to_json
def live_events(request):
    conf, date = _live_conference()
    sid = cmodels.Schedule.objects\
        .values('id')\
        .get(conference=conf.code, date=date)

    tt = TimeTable2.fromSchedule(sid['id'])
    tt.removeEventsByTag('special')
    t0 = datetime.datetime.now().time()

    tracks = settings.P3_LIVE_TRACKS.keys()
    events = {}
    for track, tevts in tt.iterOnTracks(start=('current', t0)):
        curr = None
        try:
            curr = dict(tevts[0])
            curr['next'] = dict(tevts[1])
        except IndexError:
            pass
        # Ho eliminato gli eventi special, t0 potrebbe cadere su uno di questi
        if curr and (curr['time'] + datetime.timedelta(seconds=curr['duration']*60)).time() < t0:
            curr = None

        if track not in tracks:
            continue
        events[track] = curr

    def event_url(event):
        if event.get('talk'):
            return reverse('conference-talk', kwargs={'slug': event['talk']['slug']})
        else:
            return None

    output = {}
    for track, event in events.items():
        if event is None:
            output[track] = {
                'id': None,
                'embed': settings.P3_LIVE_EMBED(request, track=track),
            }
            continue
        url = event_url(event)
        if event.get('talk'):
            speakers = [
                (
                    reverse('conference-speaker', kwargs={'slug': s['slug']}),
                    s['name'],
                    dataaccess.profile_data(s['id'])['image']
                )
                for s in event['talk']['speakers']
            ]
        else:
            speakers = None
        if event.get('next'):
            next = {
                'name': event['next']['name'],
                'url': event_url(event['next']),
                'time': event['next']['time'],
            }
        else:
            next = None
        output[track] = {
            'id': event['id'],
            'name': event['name'],
            'url': url,
            'speakers': speakers,
            'start': event['time'],
            'end': event['time'] + datetime.timedelta(seconds=event['duration'] * 60),
            'tags': event['talk']['tags'] if event.get('talk') else [],
            'embed': settings.P3_LIVE_EMBED(request, event=event),
            'next': next,
        }
    return output


