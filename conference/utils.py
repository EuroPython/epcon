# -*- coding: UTF-8 -*-
from django.conf import settings as dsettings
from django.core.mail import send_mail as real_send_mail
from django.core.urlresolvers import reverse

from conference import settings
from conference.models import VotoTalk, EventTrack

import json
import logging
import os.path
import re
import subprocess
import tempfile
from collections import defaultdict

log = logging.getLogger('conference')

def dotted_import(path):
    from importlib import import_module
    from django.core.exceptions import ImproperlyConfigured
    i = path.rfind('.')
    module, attr = path[:i], path[i+1:]

    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured('Error importing %s: "%s"' % (path, e))

    try:
        o = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define "%s"' % (module, attr))

    return o

def send_email(force=False, *args, **kwargs):
    if force is False and not settings.SEND_EMAIL_TO:
        return
    if 'recipient_list' not in kwargs:
        kwargs['recipient_list'] = settings.SEND_EMAIL_TO
    if 'from_email' not in kwargs:
        kwargs['from_email'] = dsettings.DEFAULT_FROM_EMAIL
    real_send_mail(*args, **kwargs)

def _input_for_ranking_of_talks(talks, missing_vote=5):
    """
    Given a list of talk returns the output to pass to vengine; if a user
    has not expressed a preference for a talk he was awarded the `missing_vote` value.
    """
    # If talks is a QuerySet, I don't want to interact with the database.
    talks = list(talks)
    tids = set(t.id for t in talks)

    # Join the talk ids
    cands = ' '.join(map(str, tids))
    # Join the sorted talks (by the created date)
    tie = ' '.join(str(t.id) for t in sorted(talks, key=lambda x: x.created))
    vinput = [
        '-m schulze',
        '-cands %s -tie %s' % (cands, tie),
    ]
    for t in talks:
        vinput.append('# %s - %s' % (t.id, t.title.encode('utf-8')))

    votes = VotoTalk.objects\
        .filter(talk__in=tids)\
        .order_by('user', '-vote')
    users = defaultdict(lambda: defaultdict(list))
    for vote in votes:
        users[vote.user_id][vote.vote].append(vote.talk_id)

    for votes in users.values():
        # All the unrated talks by thte user get the standard 'missing_vote' vote.
        missing = tids - set(sum(votes.values(), []))
        if missing:
            votes[missing_vote].extend(missing)

        # To express preferences in format
        # cand1 = cand2 -> the two candidates have had the same preference
        # cand1 > cand2 -> cand1 had more than cand2 preferences
        # cand1 = cand2 > cand3 -> cand1 equals cand2 both greater than cand3
        input_line = []
        ballot = sorted(votes.items(), reverse=True)
        for vote, tid in ballot:
            input_line.append('='.join(map(str, tid)))
        vinput.append('>'.join(input_line))

    return '\n'.join(vinput)

def ranking_of_talks(talks, missing_vote=5):
    import conference
    vengine = os.path.join(os.path.dirname(conference.__file__), 'utils', 'voteengine-0.99', 'voteengine.py')

    talks_map = dict((t.id, t) for t in talks)
    in_ = _input_for_ranking_of_talks(talks_map.values(), missing_vote=missing_vote)

    pipe = subprocess.Popen(
        [vengine],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        close_fds=True
    )
    out, err = pipe.communicate(in_)
    if pipe.returncode != 0:
        raise RuntimeError("voteengine.py exits with code: %s; %s" % (pipe.returncode, err))

    return [ talks_map[int(tid)] for tid in re.findall(r'\d+', out.split('\n')[-2]) ]

def voting_results():
    """
    Returns the voting results stored in the file settings.TALKS_RANKING_FILE.
    The returned list is a list of tuples (talk__id, talk__type, talk__language).
    If TALKS_RANKING_FILE is not set or does not exist the return value is None.
    """
    # FIXME: Rewrite this part with 'with open(settings.TALKS_RANKING_FILE)'
    if settings.TALKS_RANKING_FILE:
        try:
            f = file(settings.TALKS_RANKING_FILE)
        except IOError:
            pass
        else:
            results = []
            for line in f:
                pieces = line.split('-', 4)
                if len(pieces) != 5:
                    continue
                type = pieces[2].strip()
                language = pieces[3].strip()
                tid = int(pieces[1].strip())
                results.append((tid, type, language))
            return results
    return None

from datetime import datetime, date, timedelta, time
from conference.models import Event, Track

class TimeTable2(object):
    def __init__(self, sid, events):
        """
        events -> dict(track -> list(events))
        """
        self.sid = sid
        self._analyzed = False
        self.events = events
        # Track list in the right order
        self._tracks = list(Track.objects\
            .filter(schedule=sid)\
            .order_by('order')\
            .values_list('track', flat=True))

    def __str__(self):
        return 'TimeTable2: %s - %s' % (self.sid, ', '.join(self._tracks))

    def addEvents(self, events):
        from conference import dataaccess
        for e in events:
            if isinstance(e, int):
                e = dataaccess.event_data(e)
            for t in e['tracks']:
                if t not in self._tracks:
                    raise ValueError("Unknown track: %s" % t)
                try:
                    self.events[t].append(e)
                except KeyError:
                    self.events[t] = [e]
        self._analyzed = False

    def removeEventsByTag(self, *tags):
        tags = set(tags)
        for events in self.events.values():
            for ix, e in reversed(list(enumerate(events))):
                if e['tags'] & tags:
                    del events[ix]

    @classmethod
    def fromEvents(cls, sid, eids):
        from conference import dataaccess
        qs = Event.objects\
            .filter(schedule=sid, id__in=eids)\
            .values_list('id', flat=True)
        events = dataaccess.events(eids=qs)
        events.sort(key=lambda x: x['time'])
        tracks = defaultdict(list)
        for e in events:
            for t in e['tracks']:
                tracks[t].append(e)

        return cls(sid, dict(tracks))

    @classmethod
    def fromTracks(cls, tids):
        """
        If builds a TimeTable with present events in specified track.
        The resulting TimeTable will be limited to the track listed regardless
        of which track are associated with the events.
        """
        qs = EventTrack.objects\
            .filter(track__in=tids)\
            .values('event')\
            .distinct()
        sids = Track.objects\
            .filter(id__in=tids)\
            .values('schedule')\
            .distinct()
        assert len(sids) == 1
        tt = cls.fromEvents(sids[0]['schedule'], qs)
        tracks = set(Track.objects\
            .filter(id__in=tids)\
            .values_list('track', flat=True))
        for t in tt.events.keys():
            if t not in tracks:
                del tt.events[t]
        return tt

    @classmethod
    def fromSchedule(cls, sid):
        qs = EventTrack.objects\
            .filter(event__schedule=sid)\
            .values('event')\
            .distinct()
        return cls.fromEvents(sid, qs)

    def _analyze(self):
        if self._analyzed:
            return
        # step 1 - I try "stacked" events
        for t in self._tracks:
            events = {}
            timeline = []
            for e in self.events.get(t, []):
                row = (e['time'], e['time'] + timedelta(seconds=e['duration'] * 60), e['id'])
                events[e['id']] = e
                timeline.append(row)
            for ix, e1 in enumerate(timeline):
                for e2 in timeline[ix+1:]:
                    # http://stackoverflow.com/questions/9044084/efficient-data-range-overlap-calculation-in-python
                    latest_start = max(e1[0], e2[0])
                    earliest_end = min(e1[1], e2[1])
                    overlap = (earliest_end - latest_start)
                    if overlap.seconds > 0 and overlap.days >= 0:
                        for eid in (e1[2], e2[2]):
                            e = events[eid]
                            try:
                                e['intersection'] += 1
                            except KeyError:
                                e['intersection'] = 1
        self._analyzed = True

    def iterOnTracks(self, start=None):
        """
        Iterates through the events of the timetable a track at a time, returns an iterator ((track, [events]))
        """
        self._analyze()
        for track in self._tracks:
            try:
                events = self.events[track]
            except KeyError:
                continue
            if start is not None:
                if isinstance(start, time):
                    mode = 'next'
                    t0 = start
                else:
                    mode, t0 = start
                for ix, e in enumerate(events):
                    t = e['time'].time()
                    if t >= t0:
                        if t == t0:
                            break
                        if mode == 'current':
                            if ix > 0:
                                ix -= 1
                            break
                        elif mode == 'next':
                            ix += 1
                            break
                events = events[ix:]
            try:
                yield track, events
            except KeyError:
                continue

    def iterOnTimes(self, step=None):
        """
        Iterates through the events of the timetable grouping them according
        to the time start, returns a process ((time, [events]))
        """
        self._analyze()
        trasposed = defaultdict(list)
        for events in self.events.values():
            for e in events:
                trasposed[e['time']].append(e)

        step = step * 60 if step is not None else 0
        previous = None
        for time, events in sorted(trasposed.items()):
            if step and previous:
                while (time-previous).seconds > step:
                    previous = previous + timedelta(seconds=step)
                    yield previous, []
            yield time, events
            previous = time

    def limits(self):
        """
        Returns start date and the end of the TimeTable
        """
        start = end = None
        for e in self.events.values():
            if start is None or e[0]['time'] < start:
                start = e[0]['time']
            x = e[-1]['time'] + timedelta(seconds=e[-1]['duration']*60)
            if end is None or x > end:
                end = x
        return start, end

    def slice(self, start=None, end=None):
        """
        Returns a new TimeTable containing only events between start and end.
        """
        e0, e1 = self.limits()
        if start is None:
            if e0:
                start = e0.time()
        else:
            if e0:
                if start < e0.time():
                    start = e0.time()
            else:
                start = None
        if end is None:
            if e1:
                end = e1.time()
        else:
            if e1:
                if end > e1.time():
                    end = e1.time()
            else:
                end = None
        events = dict(self.events)
        if start or end:
            for track, evs in events.items():
                for ix, e in reversed(list(enumerate(evs))):
                    if start and e['time'].time() < start:
                        del evs[ix]
                    if end and e['time'].time() > end:
                        del evs[ix]

        return TimeTable2(self.sid, events)

    def adjustTimes(self, start=None, end=None):
        """
        Change the TimeTable because begin and end with the specified time (if specified).
        If necessary, are added multi events track.
        """
        tpl = {
            'id': None,
            'name': '',
            'custom': '',
            'tracks': self.events.keys(),
            'tags': set(),
            'talk': None,
            'time': None,
            'duration': None,
        }
        e0, e1 = self.limits()
        if start and e0 and start < e0.time():
            for track, events in self.events.items():
                e = dict(tpl)
                e['time'] = datetime.combine(events[0]['time'].date(), start)
                e['duration'] = (e0 - e['time']).seconds / 60
                self.events[track].insert(0, e)

        if end and e1 and end > e1.time():
            d = (datetime.combine(date.today(), end) - e1).seconds / 60
            for track, events in self.events.items():
                e = dict(tpl)
                e['time'] = e1
                e['duration'] = d
                self.events[track].append(e)

        return self

def collapse_events(tt, threshold):
    """
    Given a timetable looks for moments in time that can be "Collapsed"
    because not interesting, that do not lead to changes schedule.

    For example, a timetable with very long events.
    """
    if isinstance(threshold, int):
        threshold = { None: threshold }
    
    output = []
    for time, events in tt.iterOnTimes():
        limits = []
        durations = []
        checks = []
        for e in events:
            l = threshold.get('talk' if e['talk'] else 'custom', threshold[None])
            limits.append(l)
            durations.append(e['duration'])
            checks.append(e['duration'] > l)

        if all(checks):
            offset = min(limits)
            st = time + timedelta(seconds=offset*60)
            d = min(durations) - offset
            output.append((st, d))
    return output

class TimeTable(object):
    class Event(object):
        def __init__(self, time, row, ref, columns, rows):
            self.time = time
            self.row = row
            self.ref = ref
            self.columns = columns
            self.rows = rows

    class Reference(object):
        def __init__(self, time, row, evt, flex=False):
            self.time = time
            self.row = row
            self.evt = evt
            self.flex = flex

    def __init__(self, time_spans, rows, slot_length=15):
        self.start, self.end = time_spans
        assert self.start < self.end
        self.rows = rows
        assert self.rows
        self.slot = timedelta(seconds=slot_length*60)

        self._data = {}
        self.errors = []

    def slice(self, start=None, end=None):
        if not start:
            start = self.start
        if not end:
            end = self.end
        if end < start:
            start, end = end, start
        t2 = TimeTable(
            (start, end),
            self.rows,
            self.slot.seconds/60,
        )
        t2._data = dict(self._data)
        t2.errors = list(self.errors)

        for key in list(t2._data):
            if (start and key[0] < start) or (end and key[0] >= end):
                del t2._data[key]

        return t2

    @classmethod
    def sumTime(cls, t, td):
        return ((datetime.combine(date.today(), t)) + td).time()

    @classmethod
    def diffTime(cls, t1, t2):
        return ((datetime.combine(date.today(), t1)) - (datetime.combine(date.today(), t2)))

    def setEvent(self, time, o, duration, rows):
        assert rows
        assert not (set(rows) - set(self.rows))
        if not duration:
            next = self.findFirstEvent(self.sumTime(time, self.slot), rows[0])
            if not next:
                duration = self.diffTime(self.end, time).seconds / 60
            else:
                duration = self.diffTime(next.time, time).seconds / 60
            flex = True
        else:
            flex = False
        count = duration / (self.slot.seconds / 60)

        evt = TimeTable.Event(time, rows[0], o, count, len(rows))
        self._setEvent(evt, flex)
        for r in rows[1:]:
            ref = TimeTable.Reference(time, r, evt, flex)
            self._setEvent(ref, flex)
            
        step = self.sumTime(time, self.slot)
        while count > 1:
            for r in rows:
                ref = TimeTable.Reference(step, r, evt, flex)
                self._setEvent(ref, flex)
            step = self.sumTime(step, self.slot)
            count -= 1

    def _setEvent(self, evt, flex):
        event = evt.ref if isinstance(evt, TimeTable.Event) else evt.evt.ref
        try:
            prev = self._data[(evt.time, evt.row)]
        except KeyError:
            pass
        else:
            if isinstance(prev, TimeTable.Event):
                self.errors.append({
                    'type': 'overlap-event',
                    'time': evt.time,
                    'event': event,
                    'previous': prev.ref,
                    'msg': 'Event %s overlap %s on time %s' % (event, prev.ref, evt.time),
                })
                return
            elif isinstance(prev, TimeTable.Reference):
                # I am trying to place an event on a cell occupied by a reference,
                # a time extension of an other event.
                #
                # Se nessuno dei due eventi (il nuovo e il precedente) è flex
                # notifico un warning (nel caso uno dei due sia flex non dico
                # nulla perché gli eventi flessibili sono nati proprio per
                # adattarsi agli altri); dopodiché accorcio, se possibile,
                # l'evento precedente.
                if not prev.flex and not flex:
                    self.errors.append({
                        'type': 'overlap-reference',
                        'time': evt.time,
                        'event': event,
                        'previous': prev.evt.ref,
                        'msg': 'Event %s overlap %s on time %s' % (event, prev.evt.ref, evt.time),
                    })

                # accorcio l'evento precedente solo se è di tipo flex oppure se
                # l'evento che sto inserendo non *è* flex. Questo copre il caso
                # in cui un talk va a posizionarsi in una cella occupata da un
                # estensione di un pranzo (evento flex) oppure quando un
                # evento flex a sua volta va a coprire un estensione di un
                # altro evento flex (ad esempio due eventi custom uno dopo
                # l'altro).
                if not flex or prev.flex:
                    evt0 = prev.evt
                    columns = self.diffTime(evt.time, evt0.time).seconds / self.slot.seconds
                    for row in self.rows:
                        for e in self.iterOnRow(row, start=evt.time):
                            if isinstance(e, TimeTable.Reference) and e.evt is evt0:
                                del self._data[(e.time, e.row)]
                            else:
                                break
                    evt0.columns = columns
        self._data[(evt.time, evt.row)] = evt

    def iterOnRow(self, row, start=None, end=None):
        if start is None:
            start = self.start
        if end is None:
            end = self.end
        while start < end:
            try:
                yield self._data[(start, row)]
            except KeyError:
                pass
            start = self.sumTime(start, self.slot)

    def findFirstEvent(self, start, row):
        for evt in self.iterOnRow(row, start=start):
            if isinstance(evt, TimeTable.Reference) and evt.evt.time >= start:
                return evt.evt
            elif isinstance(evt, TimeTable.Event):
                return evt

    def columns(self):
        step = self.start
        while step < self.end:
            yield step
            step = self.sumTime(step, self.slot)

    def eventsAtTime(self, start, include_reference=False):
        """
        Returns the rows that contain an Event (and Reference if include_reference = True)
        in the past tense.
        """
        output = []
        for r in self.rows:
            try:
                cell = self._data[(start, r)]
            except KeyError:
                continue
            if include_reference or isinstance(cell, TimeTable.Event):
                output.append(cell)
        return output

    def changesAtTime(self, start):
        """
        Returns the rows that introduce a change in the past tense.
        """
        output = []
        for key, item in self._data.items():
            if not isinstance(item, TimeTable.Event):
                continue
            if key[0] == start or self.sumTime(key[0], timedelta(seconds=self.slot.seconds*item.columns)) == start:
                output.append(key)
        return output

    def byRows(self):
        output = []
        data = self._data
        for row in self.rows:
            step = self.start

            cols = []
            line = [ row, cols ]
            while step < self.end:
                cols.append({'time': step, 'row': row, 'data': data.get((step, row))})
                step = self.sumTime(step, self.slot)

            output.append(line)

        return output

    def byTimes(self):
        output = []
        data = self._data
        #if not data:
        #    return output
        step = self.start
        while step < self.end:
            rows = []
            line = [ step, rows ]
            for row in self.rows:
                rows.append({'row': row, 'data': data.get((step, row))})
            output.append(line)
            step = self.sumTime(step, self.slot)

        return output

def render_event_video_cover(eid, thumb=(256, 256)):
    """
    Helper function; utilizza la settings.VIDEO_COVER_IMAGE per generare la
    cover dell'evento passato e copiarla sotto la MEDIA_ROOT.
    """
    import os
    import os.path
    from conference import dataaccess
    from conference import settings
    from django.conf import settings as dsettings

    event = dataaccess.event_data(eid)
    conference = event['conference']
    base = os.path.join(dsettings.MEDIA_ROOT, 'conference', 'covers', conference)
    if not os.path.exists(base):
        os.makedirs(base)

    if event.get('talk'):
        fname = event['talk']['slug']
    else:
        fname = 'event-%d' % eid

    image = settings.VIDEO_COVER_IMAGE(eid)
    if image is None:
        return False
    image.save(os.path.join(base, fname + '.jpg'), 'JPEG')

    image = settings.VIDEO_COVER_IMAGE(eid, thumb=thumb)
    image.save(os.path.join(base, fname + '.jpg.thumb'), 'JPEG')

    return True

def render_badge(tickets, cmdargs=None, stderr=subprocess.PIPE):
    """
    Prepare the badges of the past tickets.

    The tickets are processed by the function settings.TICKET_BADGE_PREPARE_FUNCTION that can group them as they wish;
    each group is stored in a different directory.

    The output contains a tuple of three elements for each group returned from preparation function:
    * Name of the group (v. settings.TICKET_BADGE_PREPARE_FUNCTION)
    * Directory containing the badge
    * JSON document passed as input to the rendering function.
    """
    cmdargs = cmdargs or []
    output = []
    for group in settings.TICKET_BADGE_PREPARE_FUNCTION(tickets):
        temp_dir = tempfile.mkdtemp(prefix='%s-' % group['name'])
        args = [settings.TICKED_BADGE_PROG ] + cmdargs + [ '-c', group['plugin'], temp_dir]
        p = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
            close_fds=True,
        )
        data = json.dumps(group['tickets'])
        sout, serr = p.communicate(data)
        if p.returncode:
            log.warn('badge maker exit with "%s"', p.returncode)
            log.warn('badge maker stderr: %s', serr)
        output.append((group['name'], temp_dir, data))
    return output

def archive_dir(directory):
    from cStringIO import StringIO
    import tarfile

    archive = StringIO()
    tar = tarfile.open(fileobj=archive, mode='w:gz')

    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        if os.path.isfile(fpath):
            tar.add(fpath, arcname=fname)
    tar.close()
    return archive.getvalue()

def timetables2ical(tts, altf=lambda d, comp: d):
    from conference import ical
    from conference import dataaccess
    from datetime import timedelta
    from django.utils.html import strip_tags

    import pytz
    from pytz import timezone
    utc = pytz.utc
    tz = timezone(dsettings.TIME_ZONE)

    cal = altf({
        'uid': '1',
        'events': [],
    }, 'calendar')
    for tt in tts:
        sdata = dataaccess.schedule_data(tt.sid)
        for time, events in tt.iterOnTimes():
            uniq = set()
            for e in events:
                if e['id'] in uniq:
                    continue
                uniq.add(e['id'])
                track = strip_tags(sdata['tracks'][e['tracks'][0]].title)
                # iCal supports dates in a different timezone to UTC through TZID parameter:
                # DTSTART;TZID=Europe/Rome:20120702T093000
                #
                # So, decided to convert the time in UTC.
                start = utc.normalize(tz.localize(e['time']).astimezone(utc))
                end = utc.normalize(tz.localize(e['time'] + timedelta(seconds=e['duration']*60)).astimezone(utc))
                ce = {
                    'uid': e['id'],
                    'start': start,
                    #'duration': timedelta(seconds=e['duration']*60),
                    'end': end,
                    'location': 'Track: %s' % track,
                }
                if e['talk']:
                    url = dsettings.DEFAULT_URL_PREFIX + reverse('conference-talk', kwargs={'slug': e['talk']['slug']})
                    ce['summary'] = (e['talk']['title'], {'ALTREP': url})
                else:
                    ce['summary'] = e['name']
                cal['events'].append(ical.Event(**altf(ce, 'event')))
    return ical.Calendar(**cal)

def conference2ical(conf, altf=lambda d, comp: d):
    from conference import models

    sids = models.Schedule.objects\
        .filter(conference=conf)\
        .values_list('id', flat=True)
    tts = map(TimeTable2.fromSchedule, sids)
    return timetables2ical(tts, altf=altf)

def oembed(url, **kw):
    for pattern, sub in settings.OEMBED_URL_FIX:
        url = re.sub(pattern, sub, url)
    return settings.OEMBED_CONSUMER.embed(url, **kw).getData()
