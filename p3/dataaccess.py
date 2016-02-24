# -*- coding: UTF-8 -*-
from conference import cachef
from conference import dataaccess as cdata
from conference import models as cmodels
from assopy import models as amodels
from p3 import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

cache_me = cachef.CacheFunction(prefix='p3:')

def profile_data(uid, preload=None):
    if preload is None:
        preload = {}
    profile = cdata.profile_data(uid)
    try:
        p3p = preload['profile']
    except KeyError:
        try:
            p3p = models.P3Profile.objects\
                .select_related('profile__user')\
                .get(profile=uid)
        except models.P3Profile.DoesNotExist:
            p3p = None
    if p3p:
        try:
            interests = preload['interests']
        except KeyError:
            interests = [ t.name for t in p3p.interests.all() ]
        profile.update({
            'tagline': p3p.tagline,
            'interests': interests,
            'twitter': p3p.twitter,
            'country': p3p.country,
            'image': p3p.public_profile_image_url(),
            'image_gravatar': p3p.image_gravatar,
            'image_url': p3p.image_url,
            'spam_recruiting': p3p.spam_recruiting,
            'spam_user_message': p3p.spam_user_message,
            'spam_sms': p3p.spam_sms,
        })
    if profile['talks']:
        try:
            spk = preload['speaker']
        except KeyError:
            try:
                spk = models.SpeakerConference.objects.get(speaker=uid)
            except models.SpeakerConference.DoesNotExist:
                spk = None
        if spk:
            profile.update({
                'first_time_speaker': spk.first_time,
            })
    return profile

def _i_profile_data(sender, **kw):
    # invalidation signal is handled by cachef
    return 'profile:%s' % (kw['instance'].profile_id,)

profile_data = cache_me(
    signals=(cdata.profile_data.invalidated,),
    models=(models.P3Profile,),
    key='profile:%(uid)s')(profile_data, _i_profile_data)

def talk_data(tid, preload=None):
    if preload is None:
        preload = {}
    talk = cdata.talk_data(tid)
    try:
        p3t = preload['talk']
    except KeyError:
        p3t = models.P3Talk.objects\
            .get(talk=tid)
    talk['sub_community'] = (p3t.sub_community, p3t.get_sub_community_display())
    return talk

def _i_talk_data(sender, **kw):
    # invalidation signal is handled by cachef
    return 'talk:%s' % (kw['instance'].talk_id,)

talk_data = cache_me(
    signals=(cdata.talk_data.invalidated,),
    models=(models.P3Talk,),
    key='talk:%(tid)s')(talk_data, _i_talk_data)

def profiles_data(uids):
    cached = zip(uids, profile_data.get_from_cache([ (x,) for x in uids ]))
    missing = [ x[0] for x in cached if x[1] is cache_me.CACHE_MISS ]

    preload = {}
    profiles = models.P3Profile.objects\
        .filter(profile__in=missing)\
        .select_related('profile__user')
    tags = cmodels.ConferenceTaggedItem.objects\
        .filter(
            content_type=ContentType.objects.get_for_model(models.P3Profile),
            object_id__in=missing
        )\
        .values('object_id', 'tag__name')
    speakers = models.SpeakerConference.objects\
        .filter(speaker__in=missing)

    for p in profiles:
        preload[p.profile_id] = {
            'profile': p,
            'interests': set(),
        }
    for row in tags:
        preload[row['object_id']]['interests'].add(row['tag__name'])
    for spk in speakers:
        preload[spk.speaker_id]['speaker'] = spk

    cdata.profiles_data(missing)

    output = []
    for ix, e in enumerate(cached):
        pid, val = e
        if val is cache_me.CACHE_MISS:
            val = profile_data(pid, preload=preload[pid])
        output.append(val)

    return output

def _user_ticket(user, conference):
    q1 = user.ticket_set.all()\
        .conference(conference)

    q2 = cmodels.Ticket.objects\
        .filter(p3_conference__assigned_to=user.email)\
        .filter(fare__conference=conference)

    qs = (q1 | q2)\
        .select_related('orderitem__order', 'fare')
    return qs

def _ticket_complete(t):
    # considering complete tickets paid with bank transfer or by
    # admin.  Being the IPN notification almost simultaneous with the
    # user coming back on our site, by filtering out unconfirmed orders
    # I'm also excluding old records sitting in the db because of
    # unconfirmed paypal payments or because the user came back to
    # our site using the back button.
    try:
        order = t.orderitem.order
    except amodels.OrderItem.DoesNotExist:
        return False
    return (order.method in ('bank', 'admin')) or order.complete()

def all_user_tickets(uid, conference):
    """
    Cache-friendly version of user_tickets: returns a list of
        (ticket_id, fare_type, fare_code, complete)
    for each ticket associated to the user.
    """
    qs = _user_ticket(User.objects.get(id=uid), conference)
    output = []
    for t in qs:
        output.append((
            t.id, t.fare.ticket_type, t.fare.code,
            _ticket_complete(t)
        ))
    return output

def _i_all_user_tickets(sender, **kw):
    o = kw['instance']
    if sender is models.TicketConference:
        conference = o.ticket.fare.conference
        params = [ (o.ticket.user_id, conference) ]
        if o.assigned_to:
            try:
                uid = User.objects.get(email__iexact=o.assigned_to).id
            except User.DoesNotExist:
                pass
            else:
                params.append((uid, conference))
    elif sender is cmodels.Ticket:
        params = [ (o.user_id, o.fare.conference) ]
    else:
        uid = o.user.user_id
        try:
            conference = o.orderitem_set\
                .all()\
                .distinct()\
                .values('ticket__fare__conference')[0]
        except IndexError:
            return []
        params = [ (uid, conference) ]
    return [ 'all_user_tickets:%s:%s' % (uid, conference) for uid, conference in params ]

all_user_tickets = cache_me(
    models=(models.TicketConference, cmodels.Ticket, amodels.Order,),
    key='all_user_tickets:%(uid)s:%(conference)s')(all_user_tickets, _i_all_user_tickets)

def user_tickets(user, conference, only_complete=False):
    """
    Returns the tickets associated with the user (because s/he bought them
    or because they've been assigned to him/her)
    """
    qs = _user_ticket(user, conference)
    if not only_complete:
        return qs
    else:
        # I'm not showing tickets associated to paypal orders that are not yet
        # "complete"; as the IPN notification is almost simultaneous with the
        # return on our site, by filtering out the unconfirmed orders
        # I'm also ignoring old records sitting inthe db after the user
        # didn't confirm the paypal payment or after returning to our site
        # using the back button.
        tickets = list(qs)
        for ix, t in list(enumerate(tickets))[::-1]:
            if not _ticket_complete(t):
                del tickets[ix]
        return tickets

def conference_users(conference, speakers=True):
    """
    Returns the list of all user_ids partecipating to the conference.
    """
    ticket_qs = cmodels.Ticket.objects\
        .filter(fare__conference=conference)\
        .filter(fare__code__startswith='T')\
    # Unassigned tickets
    q1 = User.objects\
        .filter(id__in=\
            ticket_qs\
                .filter(p3_conference__assigned_to__in=(None, ''))\
                .values_list('user', flat=True)
        )\
        .values_list('id', flat=True)

    # Assigned tickets
    q2 = User.objects\
        .filter(email__in=\
            ticket_qs\
                .exclude(p3_conference__assigned_to__in=(None,''))\
                .values('p3_conference__assigned_to')
        )\
        .values_list('id', flat=True)

    if speakers:
        q3 = User.objects\
            .filter(id__in=\
                cmodels.TalkSpeaker.objects\
                    .filter(talk__conference=conference, talk__status='accepted')\
                    .values('speaker')
            )\
            .values_list('id', flat=True)
    else:
        q3 = User.objects.none()
    return q1 | q2 | q3

def tags():
    """
    Same as `conference.dataaccess.tags` but removing data about
    tags associated to a non-public profile.
    """
    from conference.dataaccess import tags as ctags
    cid = ContentType.objects.get(app_label='p3', model='p3profile').id
    hprofiles = set(models.P3Profile.objects\
        .exclude(profile__visibility__in=('m', 'p'))\
        .values_list('profile_id', flat=True))
    hset = set([(cid, pid) for pid in hprofiles])
    data = ctags()
    for tag, objects in data.items():
        data[tag] = objects - hset
    return data

tags = cache_me(
    signals=(cdata.tags.invalidated,),
    models=(models.P3Profile, cmodels.AttendeeProfile))(tags)
