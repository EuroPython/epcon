# -*- coding: UTF-8 -*-
from conference import cachef
from conference import models
from pages.models import Page

from collections import defaultdict
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import comments
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from taggit.models import TaggedItem

cache_me = cachef.CacheFunction(prefix='conf:')

def _dump_fields(o):
    from django.db.models.fields.files import FieldFile
    output = {}
    for f in o._meta.fields:
        # uso f.column invece che f.name perchè non voglio seguire le foreign
        # key
        v = getattr(o, f.column)
        if isinstance(v, FieldFile):
            # Convert uploaded files to their URLs
            try:
                #v = settings.DEFAULT_URL_PREFIX + v.url
                v = v.url
            except ValueError:
                # file not uploaded
                v = None
        output[f.name] = v
    return output

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
    if sender is Page:
        page = kw['instance']
    elif sender is TaggedItem:
        item = kw['instance']
        if not isinstance(item.content_object, Page):
            return []
        page = item.content_object
    tags = page.tags.all().values_list('name', flat=True)
    languages = page.get_languages()
    return [ 'nav:%s:%s' % (l, t) for l in languages for t in tags ]

navigation = cache_me(
    models=(Page,TaggedItem),
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
    key='deadlines:%(lang)s:%(year)s',
    timeout=5*60)(deadlines, _i_deadlines)

def sponsor(conf):
    qs = models.SponsorIncome.objects\
        .filter(conference=conf)\
        .select_related('sponsor')\
        .order_by('-income', 'sponsor__sponsor')
    output = []
    tags = defaultdict(set)
    from tagging.models import TaggedItem
    for r in TaggedItem.objects\
                .filter(
                    content_type=ContentType.objects.get_for_model(models.SponsorIncome),
                    object_id__in=qs.values('id')
                )\
                .values('object_id', 'tag__name'):
        tags[r['object_id']].add(r['tag__name'])
    for i in qs:
        data = _dump_fields(i.sponsor)
        data.update({
            'income': i.income,
            'tags': tags[i.id],
        })
        output.append(data)
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
            .values('speaker', 'helper')
    speakers = []
    for r in speakers_data:
        profile = profile_data(r['speaker'])
        speakers.append({
            'id': r['speaker'],
            'name': profile['name'],
            'slug': profile['slug'],
            'helper': r['helper'],
        })
    speakers.sort()

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

    try:
        comment_list = preload['comments']
    except KeyError:
        comment_list = list(comments.get_model().objects\
            .filter(content_type__app_label='conference', content_type__model='talk')\
            .filter(object_pk=tid, is_public=True))

    output = _dump_fields(talk)
    output.update({
        'abstract': getattr(abstract, 'body', ''),
        'speakers': speakers,
        'tags': tags,
        'events_id': event,
        'comments': comment_list,
    })
    return output

def _i_talk_data(sender, **kw):
    if sender is models.Talk:
        tids = [ kw['instance'].id ]
    elif sender is models.Speaker:
        tids = kw['instance'].talks().values('id')
    elif sender is comments.get_model():
        o = kw['instance']
        if o.content_type.app_label == 'conference' and o.content_type.model == 'talk':
            tids = [ o.object_pk ]
        else:
            tids = []
    else:
        tids = [ kw['instance'].talk_id ]

    return [ 'talk_data:%s' % x for x in tids ]

talk_data = cache_me(
    models=(models.Talk, models.Speaker, models.TalkSpeaker, comments.get_model()),
    key='talk_data:%(tid)s')(talk_data, _i_talk_data)

def talks_data(tids):
    cached = zip(tids, talk_data.get_from_cache([ (x,) for x in tids ]))
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
    comment_list = comments.get_model().objects\
        .filter(content_type__app_label='conference', content_type__model='talk')\
        .filter(object_pk__in=talks.values('id'), is_public=True)
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

    # talk_data utilizza profile_data per recuperare alcuni dati sullo speaker,
    # precarico l'elenco per minimizzare il numero di query necessario
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
    cached = zip(sids, speaker_data.get_from_cache([ (x,) for x in sids ]))
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
    Ritorna i tag utilizzati in conference associati agli oggetti che li
    utilizzano.
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

def tags_for_talks(conference=None, status=None):
    """
    Ritorna i tag utilizzati per i talk filtrandoli per conferenza e stato del
    talk.
    """
    talks = models.Talk.objects.all().values('id')
    if conference:
        talks = talks.filter(conference=conference)
    if status:
        talks = talks.filter(status=status)

    qs = models.ConferenceTag.objects\
        .filter(
            conference_conferencetaggeditem_items__content_type=ContentType.objects.get_for_model(models.Talk),
            conference_conferencetaggeditem_items__object_id__in=talks
        )\
        .annotate(count=Count('conference_conferencetaggeditem_items'))\
        .extra(select={'lname': 'lower(name)'}, order_by=['lname'])
    return list(qs)

def _i_tags_for_talks(sender, **kw):
    statuses = [ x[0] for x in models.TALK_STATUS ]
    if sender is models.Talk:
        conf = [ kw['instance'].conference ]
    else:
        conf = models.Conference.objects.all().values_list('code', flat=True)
    return [ 'talks_data:%s:%s' % (c, s) for s in statuses for c in conf ]

tags_for_talks = cache_me(
    models=(models.Talk, models.ConferenceTaggedItem, models.ConferenceTag,),
    key='talks_data:%(conference)s:%(status)s')(tags_for_talks, _i_tags_for_talks)

def events(eids=None, conf=None):
    if eids is None:
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
        .values('event', 'track__track')\
        .order_by('track__order')
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

    talks_map = {
        'by_conf': {'all': []},
        'accepted': {'all': []},
        'proposed': {'all': []},
    }
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
    cached = zip(pids, profile_data.get_from_cache([ (x,) for x in pids ]))
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

def fares(conference):
    output = []
    for f in models.Fare.objects.filter(conference=conference):
        r = _dump_fields(f)
        r.update({
            'valid': f.valid()
        })
        output.append(r)
    return output

# XXX: cache disabilitata, perché il campo 'valid' dipende dalla data di
# scadenza della Fare e questo non funziona con la cache.
#fares = cache_me(
#    models=(models.Fare,),
#    key='fares:%(conference)s')(fares, lambda sender, **kw: 'fares:%s' % kw['instance'].conference)

def user_votes(uid, conference):
    """
    Restituisce i voti che l'utente ha assegnato ai talk della conferenza
    """
    votes = models.VotoTalk.objects\
        .filter(user=uid, talk__conference=conference)
    return dict([(v.talk_id, v.vote) for v in votes])

def _i_user_votes(sender, **kw):
    o = kw['instance']
    return 'user_votes:%s:%s' % (o.user_id, o.talk.conference)

user_votes = cache_me(
    models=(models.VotoTalk,),
    key='user_votes:%(uid)s:%(conference)s')(user_votes, _i_user_votes)

def user_events_interest(uid, conference):
    """
    Restituisce gli eventi per cui l'utente ha espresso un "interesse".
    """
    interests = models.EventInterest.objects\
        .filter(user=uid, event__schedule__conference=conference)
    return dict([(x.event_id, x.interest) for x in interests ])

def _i_user_events_interest(sender, **kw):
    o = kw['instance']
    return 'user_events_interest:%s:%s' % (o.user_id, o.event.schedule.conference)

user_events_interest = cache_me(
    models=(models.EventInterest,),
    key='user_events_interest:%(uid)s:%(conference)s')(user_events_interest, _i_user_events_interest)

def conference_booking_status(conference):
    booked = models.EventBooking.objects\
        .filter(event__schedule__conference=conference)\
        .values_list('event', flat=True)\
        .distinct()
    bookable = models.Event.objects\
        .filter(bookable=True, schedule__conference=conference)\
        .values_list('id', flat=True)
    output = {}
    for e in set(list(booked) + list(bookable)):
        output[e] = models.EventBooking.objects.booking_status(e)
    return output

def _i_conference_booking_status(sender, **kw):
    if sender is models.EventBooking:
        conference = kw['instance'].event.schedule.conference
    elif sender is models.Track:
        conference = kw['instance'].schedule.conference
    elif sender is models.Event:
        conference = kw['instance'].schedule.conference
    return 'conference_booking_status:%s' % conference

conference_booking_status = cache_me(
    models=(models.EventBooking, models.Track, models.Event,),
    key='conference_booking_status:%(conference)s')(conference_booking_status, _i_conference_booking_status)

def expected_attendance(conference):
    data = models.Schedule.objects.expected_attendance(conference)
    vals = data.values()
    max_score = max([ x['score'] for x in vals ])
    for x in vals:
        x['score_normalized'] = x['score'] / (max_score or 1)
    return data

def _i_expected_attendance(sender, **kw):
    if sender is models.EventInterest:
        conf = kw['instance'].event.schedule.conference
    elif sender is models.Track:
        conf = kw['instance'].schedule.conference
    elif sender is models.EventTrack:
        conf = kw['instance'].track.schedule.conference
    return 'expected_attendance:%s' % conf

expected_attendance = cache_me(
    models=(models.EventInterest, models.Track, models.EventTrack,),
    key='expected_attendance:%(conference)s')(expected_attendance, _i_expected_attendance)

