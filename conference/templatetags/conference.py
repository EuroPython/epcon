# -*- coding: UTF-8 -*-
from __future__ import absolute_import
import mimetypes
import os
import os.path
import re
from django.utils.translation import get_language_from_request
import random
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from django import template
from django.conf import settings as dsettings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.template import defaultfilters, Context
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.safestring import mark_safe

from conference import dataaccess
from conference import models
from conference import utils
from conference import settings
from conference.settings import MIMETYPE_NAME_CONVERSION_DICT as mimetype_conversion_dict
from conference.signals import timetable_prepare
from conference.utils import TimeTable

from tagging.models import Tag
from tagging.utils import parse_tag_input

mimetypes.init()

register = template.Library()

def _lang(ctx, full=False):
    return get_language_from_request(ctx['request'], check_path=True)

def _request_cache(request, key):
    """
    Returns (or create) a linked object dictionary usable past as cache with
    visibility equal to that of the request.
    """
    try:
        return request._conf_cache[key]
    except KeyError:
        request._conf_cache[key] = {}
    except AttributeError:
        request._conf_cache = {key: {}}
    return request._conf_cache[key]

@register.simple_tag(takes_context=True)
def get_deadlines(context, limit=None, not_expired=True):
    deadlines = dataaccess.deadlines(_lang(context))
    try:
        prev = models.Conference.objects\
            .all()\
            .order_by('-conference_start')[1]
    except IndexError:
        pass
    else:
        deadlines = [
            d for d in deadlines
            if d['date'] > prev.conference_end]
    output = []
    for d in deadlines:
        if not_expired and d['expired']:
            continue
        output.append(d)
    if limit is not None:
        output = output[:limit]
    return output

@register.simple_tag(takes_context=True)
def navigation(context, page_type):
    return dataaccess.navigation(_lang(context, full=True), page_type)

@register.tag
def stuff_info(parser, token):
    """
    {% stuff_info "file_path"|variable [as var] %}
    Return the mime type and the size of the specified file
    (the file should be in the dir "stuff")
    """
    contents = token.split_contents()
    tag_name = contents[0]
    try:
        fpath = contents[1]
    except IndexError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    if len(contents) > 2:
        if len(contents) != 4 or contents[-2] != 'as':
            raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
        var_name = contents[-1]
    else:
        var_name = None

    class StuffInfoNode(template.Node):
        def __init__(self, fpath, var_name):
            if fpath.startswith('"') and fpath.endswith('"'):
                self.fpath = fpath[1:-1]
            else:
                self.fpath = template.Variable(fpath)
            self.var_name = var_name
        def render(self, context):
            try:
                fpath = self.fpath.resolve(context)
            except AttributeError:
                fpath = self.fpath
            try:
                fpath = fpath.path
            except AttributeError:
                fpath = os.path.join(settings.STUFF_DIR, 'conference', fpath)
            try:
                stat = os.stat(fpath)
            except (AttributeError, OSError) as e:
                fsize = ftype = None
            else:
                fsize = stat.st_size
                ftype = mimetypes.guess_type(fpath)[0]
            ftype = mimetype_conversion_dict.get(ftype, ftype)
            if self.var_name:
                context[self.var_name] = (ftype, fsize)
                return ''
            else:
                return "(%s %s)" % (ftype, fsize)

    return StuffInfoNode(fpath, var_name)

@register.tag
def conference_speakers(parser, token):
    """
    {% conference_speakers [ conference ] [ limit num ] [ "random" ] as var %}

    Put in var the speaker list, optionally you can filter by conference.
    """
    contents = token.split_contents()
    tag_name = contents.pop(0)
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    contents = contents[:-2]

    conference = None
    limit = None
    random = False
    while contents:
        item = contents.pop(0)
        if item == 'limit':
            limit = int(contents.pop(0))
        elif item == '"random"':
            random = True
        elif conference is None:
            conference = item
        else:
            raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    class SpeakersNode(TNode):
        def __init__(self, conference, limit, random, var_name):
            self.var_name = var_name
            if conference:
                self.conference = self._set_var(conference)
            else:
                self.conference = None
            self.limit = limit
            self.random = random
        def render(self, context):
            speakers = models.Speaker.objects.all()
            conference = self._get_var(self.conference, context)
            if self.conference:
                speakers = speakers.filter(talk__conference=conference)
            if self.random:
                speakers = speakers.order_by('?')
            if self.limit:
                speakers = speakers[:self.limit]
            context[self.var_name] = list(speakers)
            return ''
    return SpeakersNode(conference, limit, random, var_name)

class TNode(template.Node):
    def _set_var(self, v):
        if not v:
            return v
        if v.startswith('"') and v.endswith('"'):
            return v[1:-1]
        else:
            return template.Variable(v)

    def _get_var(self, v, context):
        try:
            return v.resolve(context)
        except AttributeError:
            return v

@register.assignment_tag()
def conference_talks(conference=None, status="accepted", tag=None, type=None):
    if conference is None:
        conference = [settings.CONFERENCE]
    elif isinstance(conference, basestring):
        conference = [ conference ]
    qs = models.Talk.objects\
        .filter(conference__in=conference)\
        .values_list('id', flat=True)\
        .order_by('title')
    if type is not None:
        qs = qs.filter(type=type)
    if status is not None:
        qs = qs.filter(status=status)
    if tag is not None:
        qs = qs.filter(tags__name__in=tag)

    return dataaccess.talks_data(qs)

@register.inclusion_tag('conference/render_talk_report.html', takes_context=True)
def render_talk_report(context, speaker, conference, tags):
    context.update({
        'speaker': speaker,
        'conference': conference,
        'tags': tags,
    })
    return context

# XXX - remove
def schedule_context(schedule):
    from datetime import time

    TIME_STEP = 15
    dbtracks = dict((t.track, (ix, t)) for ix, t in enumerate(schedule.track_set.all()))
    _itracks = dict(dbtracks.values())
    dbevents = defaultdict(list)
    for e in schedule.event_set.select_related('talk', 'sponsor__sponsorincome_set'):
        dbevents[e.start_time].append(e)

    eevent = lambda t: { 'time': t, 'title': '', 'track_slots': 1, 'time_slots': 1, 'talk': None, 'tags': [], 'sponsor': None }

    # I organize timetable in the structure of the events of the past schedule
    # to make them easy to handle to the template. Each entry of timetable is a line of HTML table.
    timetable = defaultdict(lambda: { 'class': [], 'events': [ None ] * len(dbtracks)} )
    prow = [ None ] * len(dbtracks)
    for rtime, events in sorted(dbevents.items()):
        row = timetable[rtime]['events']
        end = False
        for e in events:
            event = eevent(e.start_time)
            if e.talk:
                event['title'] = e.talk.title
                event['time_slots'] = e.talk.duration / TIME_STEP
                event['talk'] = e.talk
                if e.sponsor:
                    event['sponsor'] = e.sponsor
            else:
                event['title'] = e.custom

            # row has as many elements as there are tracks of the scheduler event I enter in the right place.
            tags = set( t.name for t in Tag.objects.get_for_object(e) )
            if 'end' in tags:
                end = True
                tags.remove('end')

            # Tracks is a sorted list, with numerical indices (referring to dbtracks) of
            # track affected by the event.
            tracks = sorted([ dbtracks.get(t, [None])[0] for t in tags ])
            if None in tracks:
                # the event referes to a special track (such as coffee breaks or recording),
                # yet drawn all the special events in the same way (as I spread all the available tracks)
                # a useful extension would be to give different meanings to different special tracks
                # and change behavior accordingly.
                event['track_slots'] = len(dbtracks)
                event['tags'] = [ t for t in tags if t not in dbtracks ]
                row[0] = event
            else:
                # For the moment, we don't support the case of an associated event with
                # non-adjacent track.
                event['track_slots'] = len(tracks)
                ex = tracks[0]
                event['tags'] = [ _itracks[ex].track ]
                row[ex] = event

        # I inserted a new row in the timetable, I have enough information to control the above
        # line (prow) and length the time of the events that have no indication of timeframe.
        minutes = lambda t: t.hour * 60 + t.minute
        def m2time(m):
            nh = m / 60
            nm = m - nh * 60
            return time(hour = nh, minute = nm)
        for ix, t in enumerate(zip(prow, row)):
            p, c = t
            if not p:
                continue
            diff = minutes(rtime) - minutes(p['time'])
            slots = diff / TIME_STEP
            if not p['talk']:
                p['time_slots'] = slots
            elif p['time_slots'] < slots:
                # if timeslots is smaller than expected 'step' with an empty vote.
                premature_end = minutes(p['time']) + p['talk'].duration
                new_start = m2time(premature_end)
                empty = timetable[new_start]['events']
                empty[ix] = prow[ix] = eevent(new_start)
            elif c:
                # here I have to handle the case in which the events in the top row have
                # allocated more time slots than those identified
                for x in range(c['track_slots']):
                    pc = prow[ix+x]
                    if pc and pc['time_slots'] > slots:
                        overlap_needed = ix + x
                        break
                else:
                    overlap_needed = None
                if overlap_needed is not None:
                    # time_slots is greater if I have two possibilities:
                    # 1. If the current event is marked as 'overlap' I insert it in
                    # the middle of p, by moving part of p after c.
                    # 2. If there is no "overlap" I leave it at that, the html that will
                    # result will no doubt messed up and the operator will handle the situation at hand.
                    overlap = None
                    for t in c['tags']:
                        if t.startswith('overlap'):
                            try:
                                overlap = int(t.split('-', 1)[1])
                            except IndexError:
                                overlap = 15
                            except ValueError:
                                pass
                            else:
                                c['tags'].remove(t)
                            break
                    if overlap:
                        pix = overlap_needed
                        pc = prow[pix]
                        dslots = pc['time_slots'] - slots
                        pc['time_slots'] = slots
                        # I have to calculate the start time of the second part of the talk, which is equivalent to:
                        # inizio_overlap + tempo_overlap
                        c_end = minutes(c['time']) + overlap
                        new_start = m2time(c_end)
                        empty = timetable[new_start]['events']
                        n = dict(pc)
                        n['time'] = new_start
                        n['time_slots'] = dslots
                        n['title'] = '<strong>%s</strong><br/>(seconda parte)' % (escape(pc['title']),)
                        n['talk'] = None
                        empty[pix] = n
                        row = list(row)
                        row[pix] = empty[pix]

            # c può essere None perché suo fratello copre più track oppure
            # perché c'è un buco nello schedule.
            if not c and ix and row[ix-1] and row[ix-1]['track_slots'] == 1:
                # *potrebbe* essere un buco nello schedule, per esserne certo
                # devo verificare che il corrispondente evento in prow non
                # abbia un time_slots maggiore di slots
                brother = row[ix-1]
                if not p or p['time_slots'] <= slots:
                    row[ix] = eevent(rtime)
                    row[ix]['time_slots'] = brother['time_slots']
        if end:
            timetable[rtime]['class'].append('end')
            prow = [ None ] * len(dbtracks)
        else:
            prow = list(row)
    if timetable:
        timetable[rtime]['class'].append('end')

    # I transform the dictionary in an ordered list, easier to handle for the template
    # and fill it with 'filler' to proportion the various groups of events
    # (more work in less for the template)
    timetable = sorted(timetable.items())
    offset = 0
    for ix, v in list(enumerate(timetable[:-1])):
        t, row = v
        if 'end' in row['class']:
            # arbitrary padding
            steps = 4
        else:
            next = timetable[ix+1+offset][0]
            if next:
                delta = next.hour * 60 + next.minute - (t.hour * 60 + t.minute)
                steps = delta / TIME_STEP
            else:
                steps = 1
        for x in range(steps - 1):
            timetable.insert(ix+1+offset, (None, None))
        offset += steps - 1

    return timetable

@register.inclusion_tag('conference/render_schedule.html', takes_context = True)
def render_schedule(context, schedule):
    """
    {% render_schedule schedule %}
    """
    if isinstance(schedule, int):
        sid = schedule
    elif isinstance(schedule, basestring):
        try:
            c, s = schedule.split('/')
        except ValueError:
            raise template.TemplateSyntaxError('%s is not in the form of conference/slug' % schedule)
        sid = models.Schedule.objects.values('id').get(conference=c, slug=s)['id']
    else:
        sid = schedule.id

    return {
        'sid': sid,
        'timetable': utils.TimeTable2.fromSchedule(sid),
    }

@register.filter
def timetable_iter_fixed_steps(tt, step):
    return tt.iterOnTimes(step=int(step))

# XXX - remove
@register.simple_tag(takes_context=True)
def schedule_timetable(context, schedule, start=None, end=None):
    if start:
        start = datetime.strptime(start, '%H:%M').time()
    else:
        start = None

    if end:
        end = datetime.strptime(end, '%H:%M').time()
    else:
        end = None

    tracks = models.Track.objects.by_schedule(schedule)
    request = context.get('request')
    if request:
        for ix, t in list(enumerate(tracks))[::-1]:
            if request.GET.get('show-%s' % t.track) == '0':
                del tracks[ix]

    if not tracks:
        return None
    timetable_prepare.send(schedule, tracks=tracks)

    events = list(models.Event.objects.filter(schedule=schedule).select_related('talk'))
    timetable_prepare.send(schedule, events=events, tracks=tracks)

    ts = [time(8,00), time(18,30)]
    if events:
        events.sort(key=lambda x: x.start_time)
        if events[0].start_time < ts[0]:
            ts[0] = events[0].start_time
        if events[-1].start_time >= ts[1]:
            if events[-1].talk:
                td = timedelta(seconds=60*events[-1].talk.duration)
            else:
                td = timedelta(seconds=3600)
            ts[1] = TimeTable.sumTime(events[-1].start_time, td)

    tt = TimeTable(time_spans=ts, rows=tracks)
    for e in events:
        if e.duration:
            duration = e.duration
        else:
            duration = e.talk.duration if e.talk else None
        event_tracks = set(parse_tag_input(e.track))
        rows = [ x for x in tracks if x.track in event_tracks ]
        if ('break' in event_tracks or 'special' in event_tracks) and not rows:
            rows = list(t for t in tracks if not t.outdoor)
        if not rows:
            continue
        if 'teaser' in event_tracks:
            duration = 30
        tt.setEvent(e.start_time, e, duration, rows=rows)

    timetable_prepare.send(schedule, timetable=tt)

    if start or end:
        tt = tt.slice(start, end)

    return tt

# XXX - remove
@register.simple_tag(takes_context=True)
def render_schedule_timetable(context, schedule, timetable, start=None, end=None, collapse='auto'):
    if start:
        start = datetime.strptime(start, '%H:%M').time()
    else:
        start = None
    if end:
        end = datetime.strptime(end, '%H:%M').time()
    else:
        end = None
    if start or end:
        timetable = timetable.slice(start, end)
    ctx = Context(context)
    ctx.update({
        'schedule': schedule,
        'timetable': timetable,
        'collapse': collapse,
    })
    return render_to_string('conference/render_schedule_timetable.html', ctx)

# XXX - remove
@register.simple_tag(takes_context=True)
def render_schedule_timetable_as_list(context, schedule, timetable, start=None, end=None):
    if start:
        start = datetime.strptime(start, '%H:%M').time()
    else:
        start = None
    if end:
        end = datetime.strptime(end, '%H:%M').time()
    else:
        end = None
    if start or end:
        timetable = timetable.slice(start, end)
    ctx = Context(context)
    ctx.update({
        'schedule': schedule,
        'timetable': timetable,
    })
    return render_to_string('conference/render_schedule_timetable_as_list.html', ctx)

@register.simple_tag(takes_context=True)
def overbooked_events(context, conference):
    """
    Returns the list of events for which it is expected a turnout greater than the track capacity.
    The forecast is made using the EventInterest.
    """
    c = _request_cache(context['request'], 'schedules_overbook')
    if not c:
        data = models.Schedule.objects.expected_attendance(conference)
        for k, v in data.items():
            if not v['overbook']:
                del data[k]
        c['items'] = data
    return c['items']

@register.simple_tag(takes_context=True)
def get_event_track(context, event):
    """
    Returns to the first track instance from those specified by the event, or
    None if it is a special type.
    """
    dbtracks = dict((t.track, t) for t in models.Track.objects.by_schedule(event.schedule))
    for t in set(parse_tag_input(event.track)):
        if t in dbtracks:
            return dbtracks[t]

@register.filter
def event_has_track(event, track):
    return track in set(parse_tag_input(event.track))

@register.simple_tag()
def event_row_span(timetable, event):
    ix = timetable.rows.index(event.row)
    return timetable.rows[ix:ix+event.rows]

@register.simple_tag()
def event_time_span(timetable, event, time_slot=15):
    start = datetime.combine(date.today(), event.time)
    end = start + timedelta(minutes=time_slot * event.columns)
    return start.time(), end.time()

# XXX - remove
@register.tag
def conference_schedule(parser, token):
    """
    {% conference_schedule conference schedule as var %}
    """
    contents = token.split_contents()
    tag_name = contents[0]
    try:
        conference = contents[1]
        schedule = contents[2]
        var_name = contents[4]
    except IndexError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)

    class ScheduleNode(TNode):
        def __init__(self, conference, schedule, var_name):
            self.var_name = var_name
            self.conference = self._set_var(conference)
            self.schedule = self._set_var(schedule)

        def render(self, context):
            schedule = models.Schedule.objects.get(
                conference = self._get_var(self.conference, context),
                slug = self._get_var(self.schedule, context),
            )
            context[self.var_name] = schedule_context(schedule)
            return ''

    return ScheduleNode(conference, schedule, var_name)

@register.filter
def add_number(value, arg):
    return value + float(arg)

@register.filter
def split(value, arg):
    return value.split(arg)

@register.filter
def splitonspace(value):
    return value.split(' ')

@register.filter
def image_resized(value, size='resized'):
    if isinstance(value, basestring):
        url = value
        if not url.startswith(dsettings.DEFAULT_URL_PREFIX + dsettings.MEDIA_URL):
            return url
    else:
        try:
            url = value.url
        except AttributeError:
            return ''
    try:
        dirname, basename = os.path.split(url)
    except:
        return ''
    else:
        return dirname + '/%s/%s' % (size, os.path.splitext(basename)[0] + '.jpg')

@register.filter
def intersected(value, arg):
    if not isinstance(arg, (list, tuple)):
        arg = [ arg ]
    return set(value) & set(arg)

@register.filter
def splitbysize(value, arg):
    from itertools import izip
    def grouper(n, iterable, fillvalue=None):
        "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * n
        return list(izip(*args))
    arg = int(arg)
    value = list(value)
    if len(value) % arg:
        value += [ None ] * (arg - (len(value) % arg))
    return grouper(arg, value)

@register.assignment_tag()
def conference_sponsor(conference=None, only_tags=None, exclude_tags=None):
    if conference is None:
        conference = settings.CONFERENCE
    data = dataaccess.sponsor(conference)
    if only_tags:
        t = set((only_tags,))
        data = filter(lambda x: len(x['tags'] & t)>0, data)
    if exclude_tags:
        t = set((exclude_tags,))
        data = filter(lambda x: len(x['tags'] & t)==0, data)
    return data

@register.tag
def conference_mediapartner(parser, token):
    """
    {% conference_mediapartner [ conference ] as var %}
    """
    contents = token.split_contents()
    tag_name = contents[0]
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    contents = contents[1:-2]

    conference = None
    if contents:
        conference = contents.pop(0)

    class MediaPartnerNode(TNode):
        def __init__(self, conference, var_name):
            self.var_name = var_name
            self.conference = self._set_var(conference)

        def render(self, context):
            partner = models.MediaPartner.objects.all()
            conference = self._get_var(self.conference, context)
            if conference:
                partner = partner.filter(mediapartnerconference__conference = conference)
            partner = partner.order_by('partner')
            context[self.var_name] = partner
            return ''
    return MediaPartnerNode(conference, var_name)

@register.tag
def render_page_template(parser, token):
    contents = token.split_contents()
    try:
        tag_name, arg = contents[0:2]
    except ValueError:
        raise template.TemplateSyntaxError("%r tag needs at least two arguments" % contents[0])
    if len(contents) > 2:
        if contents[-2] != 'as':
            raise template.TemplateSyntaxError("%r tag had invalid arguments" % contents[0])
        var_name = contents[-1]
    else:
        var_name = None

    class TemplateRenderer(template.Node):
        def __init__(self, arg, var_name):
            self.arg = template.Variable(arg)
            self.var_name = var_name

        def render(self, context):
            try:
                tpl = self.arg.resolve(context)
                t = template.Template(tpl)
                data = t.render(context)
                if self.var_name:
                    context[self.var_name] = data
                    return ''
                else:
                    return data
            except template.VariableDoesNotExist:
                return ''

    return TemplateRenderer(arg, var_name)

@register.tag
def conference_multilingual_attribute(parser, token):
    """
    {% conference_multilingual_attribute object attribute [as var] [fallback lang|any] %}
    """
    contents = token.split_contents()
    tag_name = contents[0]
    try:
        instance, attribute = contents[1:3]
    except ValueError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    contents = contents[3:]
    if contents and contents[0] == 'as':
        var_name = contents[1]
        contents = contents[2:]
    else:
        var_name = None

    if contents and contents[0] == 'fallback':
        fallback = contents[1]
        contents = contents[2:]
    else:
        fallback = None

    if contents:
        raise template.TemplateSyntaxError("%r had too many arguments" % tag_name)

    class AttributeNode(TNode):
        def __init__(self, instance, attribute, var_name, fallback):
            self.var_name = var_name
            self.instance = self._set_var(instance)
            self.attribute = self._set_var(attribute)
            self.fallback = self._set_var(fallback)

        def render(self, context):
            instance = self._get_var(self.instance, context)
            attribute = self._get_var(self.attribute, context)
            fallback = self._get_var(self.fallback, context)
            try:
                query = getattr(instance, attribute)
            except AttributeError:
                return ''

            contents = dict((c.language, c) for c in query.all() if (c.body and c.content == attribute))
            try:
                value = contents[context['LANGUAGE_CODE']]
            except KeyError:
                try:
                    value = contents[context['LANGUAGE_CODE'].split('-')[0]]
                except KeyError:
                    if fallback is None or not contents:
                        value = None
                    elif fallback != 'any':
                        value = contents.get(fallback)
                    else:
                        dlang = dsettings.LANGUAGES[0][0]
                        dlang_single = dsettings.LANGUAGES[0][0].split('-')[0]
                        if dlang in contents:
                            value = contents[dlang]
                        elif dlang_single in contents:
                            value = contents[dlang_single]
                        else:
                            value = contents.values()[0]
            if self.var_name:
                context[self.var_name] = value
                return ''
            else:
                return value.body if value else ''

    return AttributeNode(instance, attribute, var_name, fallback)

@register.simple_tag()
def video_cover_url(event, type='front', thumb=False):
    base = dsettings.MEDIA_URL + 'conference/covers/%s/' % event['conference']
    if event.get('talk'):
        url = base + event['talk']['slug']
    else:
        url = base + 'event-%d' % event['id']
    if thumb:
        url += '.jpg.thumb'
    else:
        url += '.jpg'
    return url

@register.assignment_tag(takes_context=True)
def embed_video(context, value, args=""):
    """
    {{ talk|embed_video:"source=[youtube, viddler, download, url.to.oembed.endpoint],width=XXX,height=XXX" }}
    """
    args = dict( map(lambda _: _.strip(), x.split('=')) for x in args.split(',') if '=' in x )
    video_url = video_path = None

    if isinstance(value, models.Talk):
        talk = value

        # Access to video may be limited (by default they are always accessible)
        if not settings.TALK_VIDEO_ACCESS(context['request'], talk):
            return ''

        if not talk.video_type or talk.video_type == 'download':
            video_url = reverse('conference-talk-video-mp4', kwargs={'slug': talk.slug })
            # The video is hosted with us, if 'talk.video_file' is None
            # probably because it was not done uploading (for convenience, once it is
            # convenient to have the files in a directory without having to passing by
            # the admin and upload them one by one).
            if talk.video_file:
                video_path = os.path.join(dsettings.MEDIA_ROOT, 'conference/videos', video_url.name)
            elif settings.VIDEO_DOWNLOAD_FALLBACK:
                for ext in ('.avi', '.mp4'):
                    fpath = os.path.join(dsettings.MEDIA_ROOT, 'conference/videos', talk.slug + ext)
                    if os.path.exists(fpath):
                        video_path = fpath
            if not video_path:
                return None
        else:
            video_url = value.video_url
    else:
        video_url = value

    if not any((video_url, video_path)):
        return None

    w = h = None
    if 'width' in args:
        w = int(args['width'])
    if 'height' in args:
        h = int(args['height'])

    output = None

    if not video_path:
        # the video must be embedded
        opts = {}
        if w:
            opts['maxwidth'] = w
        if h:
            opts['maxheight'] = h
        # SSL embed, youtube (at least) supports this
        opts['scheme'] = 'https'
        try:
            output = utils.oembed(video_url, **opts)
        except:
            output = None
    else:
        try:
            stat = os.stat(video_path)
        except:
            finfo = ''
        else:
            fsize = stat.st_size
            ftype = mimetypes.guess_type(video_path)[0]
            finfo = ' (%s %s)' % (ftype, defaultfilters.filesizeformat(fsize))

        html = '''
            <div>
                <a href="%s">Download video%s</a>
            </div>
        ''' % (video_url, finfo)
        output = {'html': html}
    if output:
        output['html'] = mark_safe(output['html'])
    return output

@register.tag
def conference_quotes(parser, token):
    """
    {% conference_quotes [ limit num ] as var %}
    """
    contents = token.split_contents()
    tag_name = contents.pop(0)
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    contents = contents[:-2]

    if contents:
        contents.pop(0)
        limit = int(contents.pop(0))

    class QuotesNode(TNode):
        def __init__(self, limit, var_name):
            self.var_name = var_name
            self.limit = limit
        def render(self, context):
            quotes = models.Quote.objects.order_by('?')
            if self.limit:
                quotes = quotes[:self.limit]
            context[self.var_name] = list(quotes)
            return ''
    return QuotesNode(limit, var_name)

@register.filter
def full_url(url):
    if not url.startswith(dsettings.DEFAULT_URL_PREFIX):
        url = dsettings.DEFAULT_URL_PREFIX + url
    return url

@register.filter
def full_name(u):
    return "%s %s" % (u.first_name, u.last_name)

@register.filter
def fare_blob(fare, field):
    try:
        blob = fare.blob
    except AttributeError:
        blob = fare['blob']

    match = re.search(r'%s\s*=\s*(.*)$' % field, blob, re.M + re.I)
    if match:
        return match.group(1).strip()
    return ''

@register.simple_tag()
def voting_data(conference):
    qs = models.VotoTalk.objects\
        .filter(talk__conference=conference)\
        .values('user')
    votes = qs.count()
    users = qs.distinct().count()
    groups = defaultdict(lambda: defaultdict(list))
    results = utils.voting_results()
    if results is not None:
        for tid, type, language in results:
            groups[type][language].append(tid)

    for k, v in groups.items():
        groups[k] = dict(v)

    return {
        'votes': votes,
        'users': users,
        'groups': dict(groups),
    }

@register.filter
def convert_twitter_links(text, args=None):
    text = re.sub(r'(https?://[^\s]*)', r'<a href="\1">\1</a>', text)
    text = re.sub(r'@([^\s:]*)', r'@<a href="http://twitter.com/\1">\1</a>', text)
    text = re.sub(r'([^&])#([^\s]*)', r'\1<a href="http://twitter.com/search?q=%23\2">#\2</a>', text)
    return mark_safe(text)

@register.simple_tag()
def randint():
    return random.randint(0, sys.maxint)

@register.filter
def truncate_chars(text, length):
    if len(text) > length:
        return text[:length-3] + '...'
    else:
        return text

# XXX - remove
@register.filter
def timetable_columns(timetable):
    """
    Returns the columns of a timetable, each element has this format
        (columns, events, collapse)
    is the number of events associated with the column TimeTable.Event collapse (True/False)
    indicates whether the column can be collapsed graphically.
    """
    output = []
    for c in timetable.columns():
        cells = events = flex_times = 0
        for evt in timetable.eventsAtTime(c, include_reference=True):
            cells += 1
            if isinstance(evt, utils.TimeTable.Event):
                events += 1
            elif isinstance(evt, utils.TimeTable.Reference) and evt.flex:
                flex_times += 1
        collapse = cells == flex_times
        output.append((c, events, collapse))
    return output

# XXX - remove
@register.simple_tag()
def timetable_cells(timetable, width, height, outer_width=None, outer_height=None, collapse='auto'):
    if outer_width is None:
        outer_width = width
    if outer_height is None:
        outer_height = height
    extra_width = outer_width - width
    extra_height = outer_height - height

    compress_width = 10
    def calc_width(col):
        if not col['collapse']:
            return width
        elif col['events'] == 0:
            return 0
        else:
            return 10

    columns = list(timetable.columns())
    col_pos = [{'time': None, 'pos': 0, 'collapse': False,}]
    next_pos = outer_width
    for c in columns:
        events = {
            'total': 0,
            'reference': 0,
            'flex': 0,
            'special': 0,
            'fixed': 0,
        }
        cells = flex_times = 0
        for evt in timetable.eventsAtTime(c, include_reference=True):
            events['total'] += 1
            if isinstance(evt, utils.TimeTable.Reference):
                if evt.flex:
                    events['flex'] += 1
                if 'break' in evt.evt.ref.track or 'special' in evt.evt.ref.track:
                    events['special'] += 1
                events['reference'] += 1
            else:
                events['fixed'] += 1
        if collapse == 'auto':
            collapse_flag = (events['fixed'] == 0 and events['special'] > 0) or (events['total'] == 0)
        elif collapse == 'always':
            collapse_flag = events['fixed'] == 0
        else:
            collapse_flag = False
        col_pos.append({'time': c, 'pos': next_pos, 'collapse': collapse_flag, 'events': events['total'], })
        next_pos = next_pos + calc_width(col_pos[-1])

    max_size = [0, 0]
    def size(time, row, cols=1, rows=1):
        for ix, _ in enumerate(col_pos):
            if _['time'] == time:
                break
        l = col_pos[ix]['pos']
        t = row * outer_height
        w = 0
        for _ in col_pos[ix:ix+cols]:
            w += calc_width(_)
        w += extra_width * (cols-1)
        h = rows * height
        h += extra_height * (rows-1)
        max_size[0] = max(max_size[0], l+w)
        max_size[1] = max(max_size[1], t+h)
        return "left: %dpx; top: %dpx; width: %dpx; height: %dpx" % (l, t, w, h)

    cells = [{
        'type': '',
        'size': size(None, 0),
    }]
    add = cells.append
    for c in columns:
        add({
            'type': 'hhmm',
            'time': c,
            'size': size(c, 0),
            'events': len(timetable.changesAtTime(c)),
        })

    for irow, _ in enumerate(timetable.byRows()):
        row, cols = _
        add({
            'type': 'track',
            'track': row,
            'size': size(None, irow+1),
        })
        for c in cols:
            evt = {
                'type': 'event',
                'time': c['time'],
                'row': c['row'],
            }
            if c['data'] is None:
                evt['event'] = None
                evt['size'] = size(c['time'], irow+1)
            elif isinstance(c['data'], utils.TimeTable.Event):
                evt['event'] = c['data']
                evt['size'] = size(c['time'], irow+1, cols=c['data'].columns, rows=c['data'].rows)
            else:
                continue
            add(evt)
    return {
        'cells': cells,
        'schedule_size': 'width: %dpx; height: %dpx' % (max_size[0], max_size[1]),
    }

@register.simple_tag(takes_context=True)
def render_fb_like(context, href=None, ref="", show_faces="true", width="100%", action="recommend", font="", colorscheme="light"):
    if not href:
        href = context['CURRENT_URL']
    data = dict(locals())
    data.pop('context')
    ctx = Context(context)
    ctx.update(data)
    return render_to_string('conference/render_fb_like.html', ctx)

@register.filter
def name_abbrv(name):
    whitelist = set(('de', 'di', 'der', 'van', 'mc', 'mac', 'le', 'cotta'))

    parts = name.split()
    if len(parts) == 1:
        return name

    parts.reverse()
    last_name = ''
    for part in parts:
        if not last_name:
            last_name = part
            continue
        if part.lower() in whitelist:
            last_name = part + ' ' + last_name
        else:
            break

    return '%s. %s' % (name[0], last_name)

@register.filter
def main_event(events):
    for e in events:
        if not 'teaser' in e.tags:
            return e

@register.filter
def teaser_event(events):
    for e in events:
        if event_has_track(e, 'teaser'):
            return e

# XXX - remove
@register.simple_tag(takes_context=True)
def get_talk_speakers(context, talk):
    c = _request_cache(context['request'], 'talk_speakers_%s' % talk.conference)
    if not c:
        c['items'] = models.TalkSpeaker.objects.speakers_by_talks(talk.conference)
    return c['items'].get(talk.id, [])


# XXX - remove
@register.simple_tag(takes_context=True)
def current_events(context, time=None):
    if time is None:
        time = datetime.now()
    try:
        schedule = models.Schedule.objects.get(date=time.date())
    except Schedule.DoesNotExist:
        return {}
    output = {}
    tt = schedule_timetable(context, schedule)
    for col in tt.byTimes():
        if col[0] > time.time():
            break
        output = dict(
            (r['row'], r['data']) for r in col[1]
        )
    else:
        output = {}
    return output

# XXX - remove
@register.simple_tag(takes_context=True)
def next_events(context, time=None):
    if time is None:
        time = datetime.now()
    try:
        schedule = models.Schedule.objects.get(date=time.date())
    except Schedule.DoesNotExist:
        return {}
    found = {}
    output = {}
    tt = schedule_timetable(context, schedule)
    for col in tt.byTimes():
        if col[0] >= time.time():
            for item in col[1]:
                row = item['row']
                data = item['data']
                if row in found and found[row] is None:
                    continue
                if data:
                    if hasattr(data, 'evt'):
                        data = data.evt.ref
                    else:
                        data = data.ref
                if data != found.get(row):
                    output[row] = item['data']
                    found[row] = None
            if not any(found.values()):
                break
        else:
            found = {}
            for item in col[1]:
                row = item['row']
                data = item['data']
                if data:
                    if hasattr(data, 'evt'):
                        data = data.evt.ref
                    else:
                        data = data.ref
                found[row] = data

    return output

@register.assignment_tag()
def current_conference():
    return models.Conference.objects.current()

@register.simple_tag()
def conference_fares(conf=settings.CONFERENCE):
    return filter(lambda f: f['valid'], dataaccess.fares(conf))

@register.simple_tag(takes_context=True)
def render_schedule_list(context, conference, exclude_tags=None, exclude_tracks=None):
    ctx = Context(context)

    events = dataaccess.events(conf=conference)
    if exclude_tags:
        exclude = set(exclude_tags.split(','))
        events = filter(lambda x: len(x['tags'] & exclude) == 0, events)

    if exclude_tracks:
        exclude = set(exclude_tracks.split(','))
        events = filter(lambda x: len(set(x['tracks']) & exclude) == 0, events)

    grouped = defaultdict(list)
    for e in events:
        grouped[e['time'].date()].append(e)
    ctx.update({
        'conference': conference,
        'events': sorted(grouped.items()),
    })
    return render_to_string('conference/render_schedule_list.html', ctx)


@register.filter
def markdown2(text, arg=''):
    from markdown2 import markdown
    extensions = [e for e in arg.split(",") if e]
    if len(extensions) > 0 and extensions[0] == "nosafe":
        extensions = extensions[1:]
        safe_mode = None
    else:
        safe_mode = "escape"

    return mark_safe(markdown(text, safe_mode=safe_mode, extras=extensions))


@register.simple_tag
def tagged_items(tag):
    return dataaccess.tags().get(tag, {})


@register.simple_tag(takes_context=True)
def tags_for_talks(context, conference=None, status="accepted"):
    if conference is None:
        conference = settings.CONFERENCE
    if not status:
        status = None
    return dataaccess.tags_for_talks(conference=conference, status=status)

@register.filter
def group_tags(tags):
    groups = defaultdict(list)
    for t in tags:
        groups[t.category].append(t)
    return sorted(groups.items())

@register.assignment_tag()
def talk_data(tid):
    return dataaccess.talk_data(tid)

@register.simple_tag()
def event_data(eid):
    event = dataaccess.event_data(eid)
    event.update({'schedule':dataaccess.schedule_data(event['schedule_id'])})
    return event

@register.assignment_tag()
def talks_data(tids, conference=None):
    data = dataaccess.talks_data(tids)
    if conference:
        data = filter(lambda x: x['conference'] == conference, data)
    return data

@register.assignment_tag()
def schedule_data(sid):
    return dataaccess.schedule_data(sid)

@register.assignment_tag()
def schedules_data(sids):
    return dataaccess.schedules_data(sids)

@register.filter
def content_type(id):
    return ContentType.objects.get(id=id)

@register.filter
def field_label(value, fieldpath):
    mname, fname = fieldpath.split('.')
    model = getattr(models, mname)
    field = model._meta.get_field_by_name(fname)[0]
    for k, v in field.choices:
        if k == value:
            return v
    return None

@register.simple_tag()
def admin_urlname_fromct(ct, action, id=None):
    r = 'admin:%s_%s_%s' % (ct.app_label, ct.model, action)
    if id is None:
        args = ()
    else:
        args = (str(id),)
    try:
        return reverse(r, args=args)
    except:
        return None

@register.simple_tag()
def profile_data(uid):
    return dataaccess.profile_data(uid)

@register.simple_tag()
def profiles_data(uids):
    return dataaccess.profiles_data(uids)

@register.filter
def beautify_url(url):
    """
    Remove the URL protocol and if it is only a hostname also the final '/'
    """
    try:
        ix = url.index('://')
    except ValueError:
        pass
    else:
        url = url[ix+3:]
    if url.endswith('/') and url.index('/') == len(url)-1:
        url = url[:-1]
    return url

@register.filter
def ordered_talks(talks, criteria="conference"):
    """
    Groups the talk for conference
    """
    if not talks:
        return []
    if isinstance(talks[0], int):
        talks = dataaccess.talks_data(talks)
    grouped = defaultdict(list)
    for t in talks:
        grouped[t['conference']].append(t)
    return sorted(grouped.items(), reverse=True)

#XXX: rimuovere, gli stessi dati sono presenti nella cache ritornata da profile_data
@register.simple_tag()
def visible_talks(talks, filter_="all"):
    """
    Filter the list by talk filter_:
    * 'all' returns all talks
    * 'accepted' returns talk only accepted
    * 'conference' returns all the talks presented at the current conference
    ( in addition to those accepted presented in previous conferences)
    """
    if not talks or filter_=="all":
        return talks
    if isinstance(talks[0], int):
        talks = dataaccess.talks_data(talks)
    if filter_ == "accepted":
        return filter(lambda x: x['status'] == 'accepted', talks)
    else:
        return  filter(lambda x: x['status'] == 'accepted' or x['conference'] == settings.CONFERENCE, talks)

@register.filter
def json_(val):
    from common.jsonify import json_dumps
    return mark_safe(json_dumps(val))

@register.filter
def eval_(x, code):
    try:
        return eval(code, {'x': x})
    except:
        return None

@register.filter
def attrib_(ob, attrib):
    try:
        return ob[attrib]
    except (KeyError, IndexError):
        return None
    except TypeError:
        try:
            iter(ob)
        except TypeError:
            return getattr(ob, attrib, None)
        else:
            return [ attrib_(x, attrib) for x in ob ]

@register.filter
def escape_amp(data):
    """
    Escape dell'&; questa funzione deve essere usata solo su del testo inserito
    dall'utente che dovrebbe essere html safe (quindi già avere &amp;) ma che
    non è detto sia corretto. Mi limito all'escape dell'& perché in alcuni casi
    è l'unico carattere che causa problemi all'xml (mentre con l'html i browser
    non hanno problemi), se si vuole fare l'escap di tutto si può usare il
    filtro di django.
    """
    return re.sub('&(?!amp;)', '&amp;', data)

@register.filter
def contains_(it, key):
    return key in it

@register.filter
def remove_duplicates(val, attr=None):
    if attr is None:
        key = lambda x: x
    else:
        def key(x):
            try:
                return x.get(attr)
            except AttributeError:
                return getattr(x, attr)

    check = set()
    output = []
    for x in val:
        k = key(x)
        if k not in check:
            output.append(x)
            check.add(k)
    return output

@register.simple_tag(takes_context=True)
def assign_(context, varname, value):
    context[varname] = value
    return ""

@register.simple_tag(takes_context=True)
def sum_(context, varname, *args):
    if not args:
        r = None
    else:
        args = filter(None, args)
        try:
            r = sum(args[1:], args[0])
        except Exception:
            r = None
    context[varname] = r
    return ""

@register.filter
def as_datetime(value, format="%Y/%m/%d"):
    return datetime.strptime(value, format)

@register.assignment_tag(takes_context=True)
def user_votes(context, uid=None, conference=None, talk_id=None):
    if uid is None:
        uid = context['request'].user.id
    if conference is None:
        conference = settings.CONFERENCE
    votes = dataaccess.user_votes(uid, conference)
    if talk_id:
        return votes.get(talk_id)
    else:
        return votes

@register.assignment_tag(takes_context=True)
def user_events_interest(context, uid=None, conference=None, event_id=None):
    if uid is None:
        uid = context['request'].user.id
    if conference is None:
        conference = settings.CONFERENCE

    ei = dataaccess.user_events_interest(uid, conference)
    if event_id:
        return ei.get(event_id, 0)
    else:
        return ei

@register.simple_tag(takes_context=True)
def conference_booking_status(context, conference=None, event_id=None):
    if conference is None:
        conference = settings.CONFERENCE
    status = dataaccess.conference_booking_status(conference)
    if event_id is not None:
        return status.get(event_id)
    else:
        return status

@register.simple_tag()
def conference_js_data(tags=None):
    """
    Javascript Initialization for the conference app. The use of 'conference_js_data'
    injects on the 'conference' window, a variable with some information about the conference.
    """
    if tags is None:
        tags = dataaccess.tags()

    cts = dict(ContentType.objects.all().values_list('id', 'model'))
    items = {}
    for t, objects in tags.items():
        key = t.name.encode('utf-8')
        if key not in items:
            items[key] = {}
        for ctid, oid in objects:
            k = cts[ctid]
            if k not in items[key]:
                items[key][k] = 0
            items[key][k] += 1

    tdata = defaultdict(list)
    for x in tags:
        tdata[x.category.encode('utf-8')].append(x.name.encode('utf-8'))

    data = {
        'tags': dict(tdata),
        'taggeditems': items,
    }

    return 'window.conference = %s;' % json_(data)
