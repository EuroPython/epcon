from collections import defaultdict
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from conference import cachef
from conference import models


cache_me = cachef.CacheFunction(prefix='conf:')


def _dump_fields(o):
    from django.db.models.fields.files import FieldFile
    output = {}
    for f in o._meta.fields:
        # use the f.column instead of the f.name, to be more generic
        v = getattr(o, f.column)
        if isinstance(v, FieldFile):
            # Convert uploaded files to their URLs
            try:
                v = v.url
            except ValueError:
                # file not uploaded
                v = None
        output[f.name] = v
    return output


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
    output = _dump_fields(schedule)
    output.update({
        'tracks': dict([ (x.track, x) for x in tracks]),
    })
    return output

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
    cached = list(zip(sids, schedule_data.get_from_cache([ (x,) for x in sids ])))
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
            .values('speaker', 'helper')
    speakers = []
    for r in speakers_data:
        profile = profile_data(r['speaker'])
        speakers.append({
            'id': r['speaker'],
            'name': profile['name'],
            'company': profile['company'],
            'slug': profile['slug'],
            'helper': r['helper'],
        })
    speakers.sort(key=lambda speaker: speaker['id'])

    try:
        tags = preload['tags']
    except KeyError:
        tags = set(talk.tags.all().values_list('name', flat=True))

    try:
        abstract = preload['abstract']
    except KeyError:
        abstract = talk.getAbstract()

    try:
        event = preload['event']
    except KeyError:
        event = list(talk.event_set.all().values_list('id', flat=True))

    output = _dump_fields(talk)
    output.update({
        'abstract': getattr(abstract, 'body', ''),
        'speakers': speakers,
        'tags': tags,
        'events_id': event,
        'comments': [],
    })
    return output

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
    cached = list(zip(tids, talk_data.get_from_cache([ (x,) for x in tids ])))
    missing = [ x[0] for x in cached if x[1] is cache_me.CACHE_MISS ]

    preload = {}
    talks = models.Talk.objects\
        .filter(id__in=missing)
    speakers_data = models.TalkSpeaker.objects\
        .filter(talk__in=talks.values('id'))\
        .values('talk', 'speaker', 'helper',)
    tags = models.ConferenceTaggedItem.objects\
        .filter(
            content_type=ContentType.objects.get_for_model(models.Talk),
            object_id__in=talks.values('id')
        )\
        .values('object_id', 'tag__name')
    abstracts = models.MultilingualContent.objects\
        .filter(
            content_type=ContentType.objects.get_for_model(models.Talk),
            object_id__in=talks.values('id')
        )
    comment_list = []
    events = models.Event.objects\
        .filter(talk__in=missing)\
        .values('talk', 'id')

    for t in talks:
        preload[t.id] = {
            'talk': t,
            'speakers_data': [],
            'tags': set(),
            'abstract': None,
            'comments': [],
            'event': [],
        }
    pids = set()
    for r in speakers_data:
        pids.add(r['speaker'])
        preload[r['talk']]['speakers_data'].append({
            'speaker': r['speaker'],
            'helper': r['helper'],
        })
    for r in tags:
        preload[r['object_id']]['tags'].add(r['tag__name'])
    for r in abstracts:
        if 'abstract' not in preload[r.object_id]:
            preload[r.object_id]['abstract'] = r
        else:
            if settings.LANGUAGE_CODE.startswith(r.language):
                preload[r.object_id]['abstract'] = r
    for r in comment_list:
        preload[int(r.object_pk)]['comments'].append(r)
    for r in events:
        preload[r['talk']]['event'].append(r['id'])

    # talk_data uses profile_data, we try to fetch all the data of the speaker
    # because we need to optimize the number of needed queries.
    profiles_data(pids)

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
        speaker = models.Speaker.objects.get(user=sid)

    try:
        talks_data = preload['talks_data']
    except KeyError:
        talks_data = models.TalkSpeaker.objects\
            .filter(speaker=speaker)\
            .values('talk__id', 'talk__title', 'talk__slug', 'talk__conference', 'talk__type')

    talks = []
    for t in talks_data:
        talks.append({
            'id': t['talk__id'],
            'conference': t['talk__conference'],
            'title': t['talk__title'],
            'slug': t['talk__slug'],
            'type': t['talk__type'],
        })

    output = _dump_fields(speaker)
    output.update({
        'talks': talks,
    })
    return output

def _i_speaker_data(sender, **kw):
    if sender is models.Speaker:
        sids = [ kw['instance'].pk ]
    elif sender is models.Talk:
        sids = kw['instance'].speakers.all().values_list('user_id', flat=True)
    elif sender is models.AttendeeProfile:
        sids = [ kw['instance'].user_id ]
    elif sender is models.TalkSpeaker:
        sids = models.TalkSpeaker.objects.filter(talk=kw['instance'].talk_id).values_list('speaker', flat=True)
    elif sender is User:
        sids = [ kw['instance'].id ]

    return [ 'speaker_data:%s' % x for x in sids ]

speaker_data = cache_me(
    models=(models.Speaker, models.Talk, models.TalkSpeaker, models.AttendeeProfile, User),
    key='speaker_data:%(sid)s')(speaker_data, _i_speaker_data)

def speakers_data(sids):
    cached = list(zip(sids, speaker_data.get_from_cache([ (x,) for x in sids ])))
    missing = [ x[0] for x in cached if x[1] is cache_me.CACHE_MISS ]

    preload = {}
    speakers = models.Speaker.objects\
        .filter(user__in=missing)
    talks = models.TalkSpeaker.objects\
        .filter(speaker__in=speakers.values('user'))\
        .values('speaker', 'talk__id', 'talk__title', 'talk__slug', 'talk__conference', 'talk__type')

    for s in speakers:
        preload[s.user_id] = {
            'speaker': s,
            'talks_data': [],
        }
    for t in talks:
        preload[t['speaker']]['talks_data'].append({
            'talk__id': t['talk__id'],
            'talk__title': t['talk__title'],
            'talk__slug': t['talk__slug'],
            'talk__conference': t['talk__conference'],
            'talk__type': t['talk__type'],
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
        tracks = event.tracks.all().values_list('track', flat=True)

    sch = schedule_data(event.schedule_id)
    tags = set(event.tags.split(','))
    if event.talk_id:
        talk = talk_data(event.talk_id)
        name = talk['title']
        duration = event.duration or talk['duration']
    else:
        talk = None
        name = event.custom
        duration = event.duration
    start_time = datetime.combine(sch['date'], event.start_time)
    return {
        'id': event.id,
        'schedule_id': event.schedule_id,
        'name': name,
        'time': start_time,
        'end_time': start_time + timedelta(seconds=duration*60),
        'conference': sch['conference'],
        'custom': event.custom,
        'abstract': event.abstract,
        'duration': duration,
        'sponsor': event.sponsor,
        'bookable': event.bookable,
        'tracks': tracks,
        'tags': tags,
        'talk': talk,
    }

def _i_event_data(sender, **kw):
    if sender is models.Event:
        ids = [ kw['instance'].id ]
    elif sender is models.Talk:
        ids = models.Event.objects.filter(talk=kw['instance']).values_list('id', flat=True)
    elif sender is models.Schedule:
        ids = kw['instance'].event_set.all().values_list('id', flat=True)
    elif sender is models.Track:
        ids = models.EventTrack.objects\
            .filter(track=kw['instance'])\
            .values_list('event', flat=True)
    return [ 'event:%s' % x for x in ids ]

event_data = cache_me(
    models=(models.Event, models.Talk, models.Schedule, models.Track),
    key='event:%(eid)s')(event_data, _i_event_data)

def tags():
    """
    Return the used tags from the associated conference with the associated
    objects.
    """
    qs = models.ConferenceTaggedItem.objects\
         .all()\
         .select_related('tag')

    tags = defaultdict(set)
    for item in qs:
        tags[item.tag].add((item.content_type_id, item.object_id))

    # Add tags which are not currently in use
    qs = models.ConferenceTag.objects.all()
    for tag in qs:
        if tag not in tags:
            tags[tag] = set()

    return dict(tags)

tags = cache_me(
    models=(models.ConferenceTaggedItem,))(tags)


def events(eids=None, conf=None):
    if eids is None:
        eids = models.Event.objects\
            .filter(schedule__conference=conf)\
            .values_list('id', flat=True)\
            .order_by('start_time')

    cached = list(zip(eids, event_data.get_from_cache([ (x,) for x in eids ])))
    missing = [ x[0] for x in cached if x[1] is cache_me.CACHE_MISS ]

    preload = {}
    events = models.Event.objects\
        .filter(id__in=missing)\
        .select_related('sponsor')
    tracks = models.EventTrack.objects\
        .filter(event__in=events)\
        .values('event', 'track__track')\
        .order_by('track__order')
    for e in events:
        preload[e.id] = {'event': e, 'tracks': []}

    for row in tracks:
        preload[row['event']]['tracks'].append(row['track__track'])

    # pre-load the cache, to be sure that event_data is not fetched from the
    # database each time.
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

def _i_profile_data(sender, **kw):
    if sender is models.AttendeeProfile:
        uids = [ kw['instance'].user_id ]
    elif sender is models.Speaker:
        uids = [ kw['instance'].user_id ]
    elif sender is models.TalkSpeaker:
        uids = models.TalkSpeaker.objects.filter(talk=kw['instance'].talk_id).values_list('speaker', flat=True)
    elif sender is User:
        uids = [ kw['instance'].id ]

    return [ 'profile:%s' % x for x in uids ]


def profile_data(uid, preload=None):
    if preload is None:
        preload = {}

    try:
        profile = preload['profile']
    except KeyError:
        profile = models.AttendeeProfile.objects\
            .select_related('user')\
            .get(user=uid)

    try:
        talks = preload['talks']
    except KeyError:
        talks = models.TalkSpeaker.objects\
            .filter(speaker__user=profile.user)\
            .values('talk', 'talk__status', 'talk__conference')

    try:
        bio = preload['bio']
    except KeyError:
        bio = profile.getBio()

    # NOTE(artcz)(2018-05-31)
    # I updated it to automatically fill the map with all available statuses.
    # (previously it was staticly defined dict).
    # However... I don't know why it's there, maybe we would be better with
    # defaultdict?
    talks_map = {talk_status: {'all': []}
                 for talk_status in models.TALK_STATUS._db_values}
    talks_map['by_conf'] = {'all': []}

    for t in talks:
        tid = t['talk']
        conf = t['talk__conference']
        status = t['talk__status']

        for k in ('by_conf', status):
            talks_map[k]['all'].append(tid)
            try:
                talks_map[k][conf].append(tid)
            except KeyError:
                talks_map[k][conf] = [tid]

    return {
        'id': profile.user_id,
        'slug': profile.slug,
        'uuid': profile.uuid,
        'first_name': profile.user.first_name,
        'last_name': profile.user.last_name,
        'name': '%s %s' % (profile.user.first_name, profile.user.last_name),
        'email': profile.user.email,
        'image': profile.image.url if profile.image else '',
        'phone': profile.phone,
        'birthday': profile.birthday,
        'personal_homepage': profile.personal_homepage,
        'company': profile.company,
        'company_homepage': profile.company_homepage,
        'job_title': profile.job_title,
        'location': profile.location,
        'bio': getattr(bio, 'body', ''),
        'visibility': profile.visibility,
        'talks': talks_map,
    }

profile_data = cache_me(
    models=(models.AttendeeProfile, models.Speaker, models.TalkSpeaker, User),
    key='profile:%(uid)s')(profile_data, _i_profile_data)

def profiles_data(pids):
    cached = list(zip(pids, profile_data.get_from_cache([ (x,) for x in pids ])))
    missing = [ x[0] for x in cached if x[1] is cache_me.CACHE_MISS ]

    preload = {}
    profiles = models.AttendeeProfile.objects\
        .filter(user__in=missing)\
        .select_related('user')
    talks = models.TalkSpeaker.objects\
        .filter(speaker__in=missing)\
        .values('speaker', 'talk', 'talk__status', 'talk__conference')
    bios = models.MultilingualContent.objects\
        .filter(
            content_type=ContentType.objects.get_for_model(models.AttendeeProfile),
            object_id__in=missing,
        )
    for p in profiles:
        preload[p.user_id] = {'profile': p, 'talks': [], 'bio': None}

    for row in talks:
        preload[row['speaker']]['talks'].append(row)

    for b in bios:
        preload[b.object_id]['bio'] = b

    output = []
    for ix, e in enumerate(cached):
        pid, val = e
        if val is cache_me.CACHE_MISS:
            val = profile_data(pid, preload=preload[pid])
        output.append(val)

    return output
