import logging
import os.path
import re
import subprocess
from datetime import datetime, date, timedelta, time
from collections import defaultdict

from django.conf import settings

from conference.models import VotoTalk, EventTrack, Event, Track


log = logging.getLogger('conference')


def dotted_import(path):
    # TODO: This is used in one place in the admin as a hack, replace its usage and retire this
    from importlib import import_module
    from django.core.exceptions import ImproperlyConfigured
    i = path.rfind('.')
    module, attr = path[:i], path[i + 1:]

    try:
        mod = import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured('Error importing %s: "%s"' % (path, e))

    try:
        o = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define "%s"' % (module, attr))

    return o


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
        missing = tids - set(sum(list(votes.values()), []))
        if missing:
            votes[missing_vote].extend(missing)

        # To express preferences in format
        # cand1 = cand2 -> the two candidates have had the same preference
        # cand1 > cand2 -> cand1 had more than cand2 preferences
        # cand1 = cand2 > cand3 -> cand1 equals cand2 both greater than cand3
        input_line = []
        ballot = sorted(list(votes.items()), reverse=True)
        for vote, tid in ballot:
            input_line.append('='.join(map(str, tid)))
        vinput.append('>'.join(input_line))

    return '\n'.join(vinput)


def ranking_of_talks(talks, missing_vote=5):
    import conference
    vengine = os.path.join(os.path.dirname(conference.__file__), 'tools', 'voteengine-0.99', 'voteengine.py')

    talks_map = dict((t.id, t) for t in talks)
    in_ = _input_for_ranking_of_talks(list(talks_map.values()), missing_vote=missing_vote)

    pipe = subprocess.Popen(
        [vengine],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        close_fds=True
    )
    out, err = pipe.communicate(in_)
    if pipe.returncode != 0:
        raise RuntimeError("voteengine.py exits with code: %s; %s" % (pipe.returncode, err))

    return [talks_map[int(tid)] for tid in re.findall(r'\d+', out.split('\n')[-2])]


def voting_results():
    """
    Returns the voting results stored in the file settings.TALKS_RANKING_FILE.
    The returned list is a list of tuples (talk__id, talk__type, talk__language).
    If TALKS_RANKING_FILE is not set or does not exist the return value is None.
    """
    if settings.CONFERENCE_TALKS_RANKING_FILE:
        try:
            with open(settings.CONFERENCE_TALKS_RANKING_FILE) as ranking_file:
                results = []
                for line in ranking_file:
                    pieces = line.split('-', 4)
                    if len(pieces) != 5:
                        continue
                    type = pieces[2].strip()
                    language = pieces[3].strip()
                    tid = int(pieces[1].strip())
                    results.append((tid, type, language))
            return results
        except OSError:
            pass
    return None


class TimeTable2(object):
    def __init__(self, sid, events):
        """
        events -> dict(track -> list(events))
        """
        self.sid = sid
        self._analyzed = False
        self.events = events
        # Track list in the right order
        self._tracks = list(Track.objects.filter(schedule=sid).order_by('order').values_list('track', flat=True))

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
        tracks = set(Track.objects.filter(id__in=tids).values_list('track', flat=True))
        for t in list(tt.events.keys()):
            if t not in tracks:
                del tt.events[t]
        return tt

    @classmethod
    def fromSchedule(cls, sid):
        qs = EventTrack.objects.filter(event__schedule=sid).values('event').distinct()
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
                for e2 in timeline[ix + 1:]:
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
        for _time, events in sorted(trasposed.items()):
            if step and previous:
                while (_time - previous).seconds > step:
                    previous = previous + timedelta(seconds=step)
                    yield previous, []
            yield _time, events
            previous = _time

    def limits(self):
        """
        Returns start date and the end of the TimeTable
        """
        start = end = None
        for e in self.events.values():
            if start is None or e[0]['time'] < start:
                start = e[0]['time']
            x = e[-1]['time'] + timedelta(seconds=e[-1]['duration'] * 60)
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
            'tracks': list(self.events.keys()),
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
