# -*- coding: UTF-8 -*-
import datetime
from collections import defaultdict

from django import http
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.shortcuts import render

from conference import models as cmodels
from conference.utils import TimeTable2


def _partner_as_event(fares):
    from conference.templatetags.conference import fare_blob
    partner = defaultdict(list)
    for f in fares:
        try:
            d = datetime.datetime.strptime(fare_blob(f, 'date'), '%Y/%m/%d').date()
            t = datetime.datetime.strptime(fare_blob(f, 'departure'), '%H:%M').time()
            dt = int(fare_blob(f, 'duration'))
        except Exception as e:
            continue
        partner[d].append({
            'duration': dt,
            'name': f['name'],
            'id': f['id'] * -1,
            'abstract': f['description'],
            'fare': f['code'],
            'schedule_id': None,
            'tags': set(['partner-program']),
            'time': datetime.datetime.combine(d, t),
            'tracks': ['partner0'],
        })
    return dict(partner)


def _build_timetables(schedules, events=None, partner=None):
    """
    Given a list of schedule ids / events and partner program returns a list
    of TimeTable of relating to past data.

    _build_timetables([1,2])

        Return two TimeTable relating to schedules 1 and 2 (events
        are retrieved from db).

    _build_timetables([1,2], events=...)

        Return two TimeTable relating to schedules 1 and 2 using only
        events specified (in this case events must be a dict that map
        id of the schedule list with the id of the events).

    _build_timetables([1,2], partner=...)

        Return least two TimeTable (others might be added to
        Because of partner program not covered by listed schedule).
        `Partner` must be compatible with the output of` _partner_as_event`.
    """
    tts = []

    if schedules and not events:
        for row in schedules:
            tt = TimeTable2.fromSchedule(row['id'])
            tts.append((row['id'], tt))
    else:
        for row in schedules:
            tt = TimeTable2.fromEvents(row['id'], events[row['id']])
            tts.append((row['id'], tt))

    if partner:
        for date, evts in partner.items():
            for ix, row in enumerate(schedules):
                if row['date'] == date:
                    sid, tt = tts[ix]
                    break
            else:
                try:
                    sid = cmodels.Schedule.objects.get(date=date).id
                except cmodels.Schedule.DoesNotExist:
                    # it would be better to be able to show it anyway
                    continue
                tt = TimeTable2.fromEvents(sid, [])
                tts.append((sid, tt))
            for e in evts:
                e['schedule_id'] = sid
                tt.addEvents([e])

    # Remove empty timetables
    def not_empty(o):
        tt = o[1]
        events = tt.events.values()
        return bool(events and events[0])
    tts = filter(not_empty, tts)

    # Sort timetables by date
    def key(o):
        # timetable has an indirect reference to the day, I need to get it
        # from one of the events.
        tt = o[1]
        events = tt.events.values()
        ev0 = events[0][0]
        return ev0['time']
    tts.sort(key=key)

    return tts


def _conference_timetables(conference):
    """ Return the TimeTable about the conference."""
    # The timetables must contain both events in the db and "artificial"
    # events from partner program
    sids = cmodels.Schedule.objects\
        .filter(conference=conference)\
        .values_list('id', flat=True)

    from conference.dataaccess import fares, schedules_data
    pfares = [ f for f in fares(conference) if f['ticket_type'] == 'partner' ]
    partner = _partner_as_event(pfares)

    schedules = schedules_data(sids)
    tts = _build_timetables(schedules, partner=partner)
    return tts


def schedule(request, conference):
    tts = _conference_timetables(conference)
    ctx = {
        'conference': conference,
        'sids': [ x[0] for x in tts ],
        'timetables': tts,
    }
    return render(request, 'p3/schedule.html', ctx)


def schedule_ics(request, conference, mode='conference'):
    if mode == 'my-schedule':
        if not request.user.is_authenticated():
            raise http.Http404()
        uid = request.user.id
    else:
        uid = None
    from p3.utils import conference2ical
    cal = conference2ical(conference, user=uid, abstract='abstract' in request.GET)
    return http.HttpResponse(list(cal.encode()), content_type='text/calendar')


def schedule_list(request, conference):
    sids = cmodels.Schedule.objects\
        .filter(conference=conference)\
        .values_list('id', flat=True)
    ctx = {
        'conference': conference,
        'sids': sids,
        'timetables': zip(sids, map(TimeTable2.fromSchedule, sids)),
    }
    return render(request, 'p3/schedule_list.html', ctx)


@login_required
def jump_to_my_schedule(request):
    return redirect('p3-schedule-my-schedule', conference=settings.CONFERENCE_CONFERENCE)


@login_required
def my_schedule(request, conference):
    qs = cmodels.Event.objects\
        .filter(eventinterest__user=request.user, eventinterest__interest__gt=0)\
        .filter(schedule__conference=conference)\
        .values('id', 'schedule')

    events = defaultdict(list)
    for x in qs:
        events[x['schedule']].append(x['id'])

    qs = cmodels.EventBooking.objects\
        .filter(user=request.user, event__schedule__conference=conference)\
        .values('event', 'event__schedule')
    for x in qs:
        events[x['event__schedule']].append(x['event'])

    qs = cmodels.Ticket.objects\
        .filter(user=request.user)\
        .filter(fare__conference=conference, fare__ticket_type='partner')\
       .values_list('fare', flat=True)

    from conference.dataaccess import fares, schedules_data
    pfares = [ f for f in fares(conference) if f['id'] in qs ]
    partner = _partner_as_event(pfares)

    schedules = schedules_data(events.keys())
    tts = _build_timetables(schedules, events=events, partner=partner)
    ctx = {
        'conference': conference,
        'sids': [ x[0] for x in tts ],
        'timetables': tts,
    }
    return render(request, 'p3/my_schedule.html', ctx)

