# -*- coding: UTF-8 -*-
from conference import cachef
from conference import models
from pages.models import Page

from collections import defaultdict
from datetime import datetime

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from tagging.models import Tag, TaggedItem
from tagging.utils import parse_tag_input

cache_me = cachef.CacheFunction(prefix='conf:')

def navigation(lang, page_type):
    pages = []
    qs = Page.objects\
        .published()\
        .filter(tags__name=page_type)\
        .filter(content__language=lang, content__type='slug')\
        .distinct()\
        .order_by('tree_id', 'lft')
    for p in qs:
        pages.append({
            'url': p.get_absolute_url(language=lang),
            'slug': p.slug(language=lang),
            'title': p.title(language=lang),
        })
    return pages

def _i_navigation(sender, **kw):
    page = kw['instance']
    languages = page.get_languages()
    tags = page.tags.all().values_list('name', flat=True)
    return [ 'nav:%s:%s' % (l, t) for l in languages for t in tags ]

navigation = cache_me(
    models=(Page,),
    key='nav:%(lang)s:%(page_type)s')(navigation, _i_navigation)

def _i_deadlines(sender, **kw):
    years = set(x.year for x in models.Deadline.objects.all().values_list('date', flat=True))
    years.add(None)
    languages = set([ l[0] for l in settings.LANGUAGES ])
    return [ 'deadlines:%s:%s' % (l, y) for l in languages for y in years ]

def deadlines(lang, year=None):
    qs = models.Deadline.objects\
        .all()\
        .order_by('date')
    if year:
        qs = qs.filter(date__year=year)
    output = []
    for d in qs:
        try:
            content = d.content(lang, False)
        except models.DeadlineContent.DoesNotExist:
            headline = body = ''
        else:
            headline = content.headline
            body = content.body

        output.append({
            'date': d.date,
            'expired': d.isExpired(),
            'headline': headline,
            'body': body,
        })
    return output

deadlines = cache_me(
    models=(models.Deadline, models.DeadlineContent),
    key='deadlines:%(lang)s:%(year)s')(deadlines, _i_deadlines)

def sponsor(conf):
    qs = models.SponsorIncome.objects\
        .filter(conference=conf)\
        .select_related('sponsor')\
        .order_by('-income', 'sponsor__sponsor')
    output = []
    tags = defaultdict(set)
    for r in TaggedItem.objects\
                .filter(
                    content_type=ContentType.objects.get_for_model(models.SponsorIncome),
                    object_id__in=qs.values('id')
                )\
                .values('object_id', 'tag__name'):
        tags[r['object_id']].add(r['tag__name'])
    for i in qs:
        output.append({
            'sponsor': i.sponsor,
            'income': i.income,
            'tags': tags[i.id],
        })
    return output

def _i_sponsor(sender, **kw):
    income = []
    if sender is models.Sponsor:
        income = kw['instance'].sponsorincome_set.all()
    else:
        income = [ kw['instance'] ]

    return [ 'sponsor:%s' % x.conference for x in income ]

sponsor = cache_me(
    models=(models.Sponsor, models.SponsorIncome,),
    key='sponsor:%(conf)s')(sponsor, _i_sponsor)

def schedule_data(sid, preload=None):
    if preload is None:
        preload = {}

    try:
        schedule = preload['schedule']
    except KeyError:
        schedule = models.Schedule.objects.get(id=sid)

    try:
        tracks = preload['tracks']
    except KeyError:
        tracks = models.Track.objects\
            .filter(schedule=schedule)\
            .order_by('order')
    return {
        'schedule': schedule,
        'tracks': list(tracks),
    }

def _i_schedule_data(sender, **kw):
    if sender is models.Schedule:
        sid = kw['instance'].id
    else:
        sid = kw['instance'].schedule_id
    return 'schedule:%s' % sid

schedule_data = cache_me(
    models=(models.Schedule, models.Track),
    key='schedule:%(sid)s')(schedule_data, _i_schedule_data)

def schedules_data(sids):
    cached = zip(sids, schedule_data.get_from_cache([ (x,) for x in sids ]))
    missing = [ x[0] for x in cached if x[1] is cache_me.CACHE_MISS ]

    preload = {}
    schedules = models.Schedule.objects\
        .filter(id__in=missing)
    tracks = models.Track.objects\
        .filter(schedule__in=schedules)\
        .order_by('order')

    for s in schedules:
        preload[s.id] = {
            'schedule': s,
            'tracks': [],
        }
    for t in tracks:
        preload[t.schedule_id]['tracks'].append(t)

    output = []
    for ix, e in enumerate(cached):
        sid, val = e
        if val is cache_me.CACHE_MISS:
            val = schedule_data(sid, preload=preload[sid])
        output.append(val)

    return output

def talk_data(tid, preload=None):
    if preload is None:
        preload = {}
    try:
        talk = preload['talk']
    except KeyError:
        talk = models.Talk.objects.get(id=tid)

    try:
        speakers_data = preload['speakers_data']
    except KeyError:
        speakers_data = models.TalkSpeaker.objects\
            .filter(talk=tid)\
            .values('speaker', 'helper', 'speaker__name', 'speaker__slug',)
    speakers = []
    for r in speakers_data:
        speakers.append({
            'id': r['speaker'],
            'name': r['speaker__name'],
            'slug': r['speaker__slug'],
            'helper': r['helper'],
        })
    speakers.sort()

    try:
        tags = preload['tags']
    except KeyError:
        tags = set( t.name for t in Tag.objects.get_for_object(talk) )

    return {
        'talk': talk,
        'speakers': speakers,
        'tags': tags,
    }

def _i_talk_data(sender, **kw):
    if sender is models.Talk:
        tids = [ kw['instance'].id ]
    elif sender is models.Speaker:
        tids = kw['instance'].talks().values('id')
    else:
        tids = [ kw['instance'].talk_id ]

    return [ 'talk_data:%s' % x for x in tids ]
        
talk_data = cache_me(
    models=(models.Talk, models.Speaker, models.TalkSpeaker),
    key='talk_data:%(tid)s')(talk_data, _i_talk_data)

def talks_data(tids):
    cached = zip(tids, talk_data.get_from_cache([ (x,) for x in tids ]))
    missing = [ x[0] for x in cached if x[1] is cache_me.CACHE_MISS ]

    preload = {}
    talks = models.Talk.objects\
        .filter(id__in=missing)
    speakers_data = models.TalkSpeaker.objects\
        .filter(talk__in=talks.values('id'))\
        .values('talk', 'speaker', 'helper', 'speaker__name', 'speaker__slug',)
    tags = TaggedItem.objects\
        .filter(
            content_type=ContentType.objects.get_for_model(models.Talk),
            object_id__in=talks.values('id')
        )\
        .values('object_id', 'tag__name')

    for t in talks:
        preload[t.id] = {
            'talk': t,
            'speakers_data': [],
            'tags': set(),
        }
    for r in speakers_data:
        preload[r['talk']]['speakers_data'].append({
            'speaker': r['speaker'],
            'helper': r['helper'],
            'speaker__name': r['speaker__name'],
            'speaker__slug': r['speaker__slug'],
        })
    for r in tags:
        preload[r['object_id']]['tags'].add(r['tag__name'])

    output = []
    for ix, e in enumerate(cached):
        tid, val = e
        if val is cache_me.CACHE_MISS:
            val = talk_data(tid, preload=preload[tid])
        output.append(val)

    return output

def speaker_data(sid, preload=None):
    if preload is None:
        preload = {}

    try:
        speaker = preload['speaker']
    except KeyError:
        speaker = models.Speaker.objects\
            .select_related('user')\
            .get(id=sid)

    try:
        talks_data = preload['talks_data']
    except KeyError:
        talks_data = models.TalkSpeaker.objects\
            .filter(speaker=speaker)\
            .values('talk__id', 'talk__title', 'talk__slug')

    talks = []
    for t in talks_data:
        talks.append({
            'id': t['talk__id'],
            'title': t['talk__title'],
            'slug': t['talk__slug'],
        })

    return {
        'speaker': speaker,
        'talks': talks,
    }

def _i_speaker_data(sender, **kw):
    if sender is models.Speaker:
        sids = [ kw['instance'].pk ]
    elif sender is models.Talk:
        sids = kw['instance'].speakers.all().values_list('user_id', flat=True)
    else:
        sids = [ kw['instance'].speaker_id ]

    return [ 'speaker_data:%s' % x for x in sids ]
        
speaker_data = cache_me(
    models=(models.Speaker, models.Talk, models.TalkSpeaker),
    key='speaker_data:%(sid)s')(speaker_data, _i_speaker_data)

def speakers_data(sids):
    cached = zip(sids, speaker_data.get_from_cache([ (x,) for x in sids ]))
    missing = [ x[0] for x in cached if x[1] is cache_me.CACHE_MISS ]

    preload = {}
    speakers = models.Speaker.objects\
        .filter(id__in=missing)\
        .select_related('user')
    talks = models.TalkSpeaker.objects\
        .filter(speaker__in=speakers.values('id'))\
        .values('speaker', 'talk__id', 'talk__title', 'talk__slug')

    for s in speakers:
        preload[s.id] = {
            'speaker': s,
            'talks_data': [],
        }
    for t in talks:
        preload[t['speaker']]['talks_data'].append({
            'talk__id': t['talk__id'],
            'talk__title': t['talk__title'],
            'talk__slug': t['talk__slug'],
        })

    output = []
    for ix, e in enumerate(cached):
        sid, val = e
        if val is cache_me.CACHE_MISS:
            val = speaker_data(sid, preload=preload[sid])
        output.append(val)

    return output
    
def event_data(eid, preload=None):
    if preload is None:
        preload = {}
    try:
        event = preload['event']
    except KeyError:
        event = models.Event.objects\
            .select_related('sponsor')\
            .get(id=eid)

    try:
        tracks = preload['tracks']
    except KeyError:
        print 'miss', preload
        tracks = event.tracks.all().values_list('track', flat=True)

    sch = schedule_data(event.schedule_id)
    tags = set(parse_tag_input(event.track))
    if event.talk_id:
        output = talk_data(event.talk_id)
        name = output['talk'].title
    else:
        output = {}
        name = event.custom
    output.update({
        'id': event.id,
        'name': name,
        'time': datetime.combine(sch['schedule'].date, event.start_time),
        'custom': event.custom,
        'duration': event.duration,
        'sponsor': event.sponsor,
        'tracks': tracks,
        'tags': tags,
    })
    return output

def tags():
    """
    Ritorna i tag utilizzati in conference associati agli oggetti che li
    utilizzano.
    """
    qs = models.ConferenceTaggedItem.objects\
        .all()\
        .select_related('tag')

    tags = defaultdict(set)
    for item in qs:
        t = tags[item.tag]
        t.add((item.content_type_id, item.object_id))

    return dict(tags)

tags = cache_me(
    models=(models.ConferenceTaggedItem,))(tags)

def _i_event_data(sender, **kw):
    if sender is models.Event:
        ids = [ kw['instance'].id ]
    elif sender is models.Talk:
        ids = models.Event.objects.filter(talk=kw['instance']).values_list('id', flat=True)
    return [ 'event:%s' % x for x in ids ]

event_data = cache_me(
    models=(models.Event, models.Talk, models.Schedule, models.Track),
    key='event:%(eid)s')(event_data, _i_event_data)

def events(conf):
    eids = models.Event.objects\
        .filter(schedule__conference=conf)\
        .values_list('id', flat=True)\
        .order_by('start_time')

    cached = zip(eids, event_data.get_from_cache([ (x,) for x in eids ]))
    missing = [ x[0] for x in cached if x[1] is cache_me.CACHE_MISS ]

    preload = {}
    events = models.Event.objects\
        .filter(id__in=missing)\
        .select_related('sponsor')
    tracks = models.EventTrack.objects\
        .filter(event__in=events)\
        .values('event', 'track__track')
    for e in events:
        preload[e.id] = {'event': e, 'tracks': []}

    for row in tracks:
        preload[row['event']]['tracks'].append(row['track__track'])

    # precarico le cache per essere sicuro che event_data non debba toccare il
    # database per ogni evento
    talks_data(
        models.Talk.objects\
            .filter(id__in=events.values('talk'))\
            .values_list('id', flat=True)
    )

    schedules_data(
        models.Schedule.objects\
            .filter(id__in=events.values('schedule_id').distinct())\
            .values_list('id', flat=True)
    )

    output = []
    for ix, e in enumerate(cached):
        eid, val = e
        if val is cache_me.CACHE_MISS:
            val = event_data(eid, preload=preload[eid])
        output.append(val)

    return output
