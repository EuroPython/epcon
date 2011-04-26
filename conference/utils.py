# -*- coding: UTF-8 -*-
from django.conf import settings as dsettings
from django.core.cache import cache
from django.core.mail import send_mail as real_send_mail

from conference import models
from conference import settings

import os.path
import re
import subprocess
import urllib2
from collections import defaultdict

def send_email(force=False, *args, **kwargs):
    if force is False and not settings.SEND_EMAIL_TO:
        return
    if 'recipient_list' not in kwargs:
        kwargs['recipient_list'] = settings.SEND_EMAIL_TO
    if 'from_email' not in kwargs:
        kwargs['from_email'] = dsettings.DEFAULT_FROM_EMAIL
    real_send_mail(*args, **kwargs)

def _input_for_ranking_of_talks(talks, missing_vote=5):
    import conference
    vengine = os.path.join(os.path.dirname(conference.__file__), 'utils', 'voteengine-0.99', 'voteengine.py')
    cands = ' '.join(map(str, (t.id for t in talks)))
    tie = ' '.join(str(t.id) for t in sorted(talks, key=lambda x: x.created))
    vinput = [
        '-m schulze',
        '-cands %s -tie %s' % (cands, tie),
    ]
    for t in talks:
        vinput.append('# %s - %s' % (t.id, t.title.encode('utf-8')))

    votes = models.VotoTalk.objects.filter(talk__in=talks).order_by('user', '-vote')
    users = defaultdict(lambda: defaultdict(list)) #dict((t.id, 5) for t in talks))
    for vote in votes:
        users[vote.user_id][vote.vote].append(vote.talk_id)

    talks_ids = set(t.id for t in talks)
    for votes in users.values():
        missing_talks = talks_ids - set(sum(votes.values(), []))
        votes[missing_vote].extend(missing_talks)

        ballot = sorted(votes.items(), reverse=True)
        input_line = []
        for vote, talks in ballot:
            input_line.append('='.join(map(str, talks)))
        vinput.append('>'.join(input_line))

    return '\n'.join(vinput)

def ranking_of_talks(talks, missing_vote=5):
    import conference
    vengine = os.path.join(os.path.dirname(conference.__file__), 'utils', 'voteengine-0.99', 'voteengine.py')
    talks_map = dict((t.id, t) for t in talks)
    in_ = _input_for_ranking_of_talks(talks, missing_vote=missing_vote)

    pipe = subprocess.Popen([ vengine ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    out, err = pipe.communicate(in_)

    return [ talks_map[int(tid)] for tid in re.findall(r'\d+', out.split('\n')[-2]) ]

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
            tweets = client.GetUserTimeline(screen_name, count=count)
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

from datetime import datetime, date, timedelta

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
        t2 = TimeTable(
            (start if start else self.start, end if end else self.end),
            self.rows,
            self.slot.seconds/60,
        )
        t2._data = dict(self._data)
        t2.errors = list(self.errors)

        for key in list(t2._data):
            if (start and key[0] < start) or (end and key[0] >= end):
                del t2._data[key]

        return t2

    def sumTime(self, t, td):
        return ((datetime.combine(date.today(), t)) + td).time()

    def diffTime(self, t1, t2):
        return ((datetime.combine(date.today(), t1)) - (datetime.combine(date.today(), t2)))

    def setEvent(self, time, o, duration, rows):
        assert rows
        assert not (set(rows) - set(self.rows))
        if not duration:
            next = self.findFirstEvent(time, rows[0])
            if not next:
                duration = self.diffTime(self.end, time).seconds / 60
            else:
                duration = self.diffTime(next.time, time).seconds / 60
            flex = True
        else:
            flex = False
        count = duration / (self.slot.seconds / 60)

        evt = TimeTable.Event(time, rows[0], o, count, len(rows))
        self._setEvent(evt)
        for r in rows[1:]:
            ref = TimeTable.Reference(time, r, evt, flex)
            self._setEvent(ref)
            
        step = self.sumTime(time, self.slot)
        while count > 1:
            for r in rows:
                ref = TimeTable.Reference(step, r, evt, flex)
                self._setEvent(ref)
            step = self.sumTime(step, self.slot)
            count -= 1

    def _setEvent(self, evt):
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
                if not prev.flex:
                    self.errors.append({
                        'type': 'overlap-reference',
                        'time': evt.time,
                        'event': event,
                        'previous': prev.evt.ref,
                        'msg': 'Event %s overlap %s on time %s' % (event, prev.evt.ref, evt.time),
                    })
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
            if isinstance(evt, TimeTable.Reference):
                return evt.evt
            else:
                return evt

    def columns(self):
        step = self.start
        while step < self.end:
            yield step
            step = self.sumTime(step, self.slot)

    def eventsAtTime(self, start, include_reference=False):
        """
        ritorna le righe che contengono un Event (e un Reference se
        include_reference=True) al tempo passata.
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
