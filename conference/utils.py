# -*- coding: UTF-8 -*-
from django.conf import settings as dsettings
from django.core.cache import cache
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
import urllib2
from collections import defaultdict

log = logging.getLogger('conference')

def dotted_import(path):
    from django.utils.importlib import import_module
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
    Dato un elenco di talk restituisce l'input da passare a vengine; se un
    utente non ha espresso una preferenza per un talk gli viene assegnato il
    valore `missing_vote`.
    """
    # se talks è un QuerySet evito di interrogare il db più volte
    talks = list(talks)
    tids = set(t.id for t in talks)
    # come candidati uso gli id dei talk...
    cands = ' '.join(map(str, tids))
    # e nel caso di pareggi faccio vincere il talk presentato prima
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
        # tutti i talk non votati dall'utente ottengono il voto standard
        # `missing_vote`
        missing = tids - set(sum(votes.values(), []))
        if missing:
            votes[missing_vote].extend(missing)

        # per esprimere le preferenze nel formati di vengin:
        #   cand1=cand2 -> i due candidati hanno avuto la stessa preferenza
        #   cand1>cand2 -> cand1 ha avuto più preferenze di cand2
        #   cand1=cand2>cand3 -> cand1 uguale a cand2 entrambi maggiori di cand3
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

    return [ talks_map[int(tid)] for tid in re.findall(r'\d+', out.split('\n')[-2]) ]

def voting_results():
    """
    Restituisce i risultati della votazione memorizzati nel file
    settings.TALKS_RANKING_FILE. La lista ritornata è un elenco di tuple
    (talk__id, talk__type, talk__language). Se TALKS_RANKING_FILE non è settato
    o non esiste il valore di ritorno è None.
    """
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

def latest_tweets(screen_name, count):
    import twitter
    key = 'conf:latest:tweets:%s:%s' % (screen_name, count)
    data = cache.get(key)
    if data is None:
        client = twitter.Api()
        # il modulo twitter fornisce un meccanismo di caching, ma
        # preferisco disabilitarlo per due motivi:
        #
        # 1. voglio usare la cache di django, in questo modo modificando i
        # settings modifico anche la cache per twitter
        # 2. di default, ma è modificabile con le api pubbliche, la cache
        # del modulo twitter è file-based e sbaglia a decidere la directory
        # in cui salvare i file; finisce per scrivere in
        # /tmp/python.cache_nobody/... che non è detto sia scrivibile
        # (sopratutto se la directory è stata creata da un altro processo
        # che gira con un utente diverso).
        client.SetCache(None)
        try:
            tweets = client.GetUserTimeline(screen_name, count=count, include_rts=True)
        except (ValueError, urllib2.HTTPError):
            # ValueError: a volte twitter.com non risponde correttamente, e
            # twitter (il modulo) non verifica. Di conseguenza viene
            # sollevato un ValueError quando twitter (il modulo) tenta
            # parsare un None come se fosse una stringa json.

            # HTTPError: a volte twitter.com non risponde proprio :) (in
            # realtà risponde con un 503)

            # Spesso questi errori durano molto poco, ma per essere gentile
            # con twitter cacho un risultato nullo per poco tempo.
            tweets = []
        except:
            # vista la stabilità di twitter meglio cachare tutto per
            # evitare errori sul nostro sito
            tweets = []
        data = [{
                    "text": tweet.GetText(),
                    "timestamp": tweet.GetCreatedAtInSeconds(),
                    "followers_count": tweet.user.GetFollowersCount(),
                    "id": tweet.GetId(),
                } for tweet in tweets]
        cache.set(key, data, 60 * 5)
    return data

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
        # elenco track nell'ordine giusto
        self._tracks = list(Track.objects\
            .filter(schedule=sid)\
            .order_by('order')\
            .values_list('track', flat=True))

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
        Costruisce una TimeTable con gli eventi presenti nelle track
        specificate. La Timetable risultante verrà limitata alle sole track
        elencate indipendentemente da quali track sono associate agli eventi.
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
        # step 1 - cerco eventi "sovrapposti"
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

    def iterOnTracks(self):
        """
        Itera sugli eventi della timetable una track per volta, restituisce un
        iter((track, [events])).
        """
        self._analyze()
        for t in self._tracks:
            try:
                yield t, self.events[t]
            except KeyError:
                continue

    def iterOnTimes(self, step=None):
        """
        Itera sugli eventi della timetable raggruppandoli a seconda del tempo
        di inizio, restituisce un iter((time, [events])).
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
        Restituisce data di inizio e fine della TimeTable
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
        Restituisce un nuovo TimeTable contenente solo gli eventi compresi tra
        start e end.
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
        Modifica la TimeTable perchè inizi e termini con i tempi specificati
        (se specificati).  Se necessario vengono aggiunti degli eventi multi
        traccia.
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
    Data una timetable cerca i momenti temporali che possono essere
    "collassati" perchè non interessanti, che non portano modifiche allo
    schedule.

    Ad esempio una timetable con eventi molto lunghi 
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
                # sto cercando di inserire un evento su una cella occupata da
                # un reference, un estensione temporale di un altro evento. 
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
        ritorna le righe che contengono un Event (e un Reference se
        include_reference=True) al tempo passato.
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
        ritorna le righe che introducono un cambiamento al tempo passato.
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

    @classmethod
    def buildFromTracks(cls, tracks, timespan=(time(8, 00), time(18, 30)), adjust_ts=True):
        events = list(EventTrack.objects\
            .filter(track__in=tracks)\
            .values('event', 'event__start_time', 'event__talk__duration', 'event__duration', 'track'))
        print events
        if adjust_ts:
            events.sort(key=lambda x: x['event__start_time'])
            timespan = list(timespan)
            if events[0]['event__start_time'] < timespan[0]:
                timespan[0] = events[0]['event__start_time']
            if events[-1]['event__start_time'] >= timespan[1]:
                if events[-1]['event__talk__duration']:
                    td = timedelta(seconds=60*events[-1]['event__talk__duration'])
                else:
                    td = timedelta(seconds=3600)
                timespan[1] = TimeTable.sumTime(events[-1]['start_time'], td)
        tt = cls(timespan, tracks)

        #tmap = dict([
        etracks = defaultdict(list)
        for e in events:
            etracks[e['event']].append(e['track'])

        for e in events:
            if e['event__duration']:
                duration = e['event__duration']
            else:
                duration = e['event__talk__duration']
            event_tracks = set(parse_tag_input(e.track))
            rows = [ x for x in tracks if x.track in event_tracks ]
            if ('break' in event_tracks or 'special' in event_tracks) and not rows:
                rows = list(t for t in tracks if not t.outdoor)
            if not rows:
                continue
            if 'teaser' in event_tracks:
                duration = 30
            tt.setEvent(e.start_time, e, duration, rows=rows)

        return tt

def render_badge(tickets, cmdargs=None):
    if cmdargs is None:
        cmdargs = []
    files = []
    for group in settings.TICKET_BADGE_PREPARE_FUNCTION(tickets):
        tfile = tempfile.NamedTemporaryFile(suffix='.tar')
        args = [settings.TICKED_BADGE_PROG, '-o', tfile.name] + cmdargs + list(group['args'])
        p = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
        )
        sout, serr = p.communicate(json.dumps(group['tickets']))
        if p.returncode:
            log.warn('badge maker exit with "%s"', p.returncode)
            log.warn('badge maker stderr: %s', serr)
        tfile.seek(0)
        files.append(tfile)
    return files

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
                # ical supporta date in una timezone diversa da UTC attraverso
                # il parametro TZID:
                # DTSTART;TZID=Europe/Rome:20120702T093000
                #
                # Il problema nel non usare UTC è che il nome della timezone è
                # solo un identificativo locale al file ica, e deve esistere
                # una struttura VTIMEZONE che ne descrive le proprietà.
                #
                # Per questo ho deciso di convertire i tempi in UTC
                start = utc.normalize(tz.localize(e['time']).astimezone(utc))
                ce = {
                    'uid': e['id'],
                    'start': start,
                    'duration': timedelta(seconds=e['duration']*60),
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

