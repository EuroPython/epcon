# -*- coding: UTF-8 -*-
from conference import cachef
from conference import dataaccess as cdata
from conference import models as cmodels
from p3 import models
from django.contrib.auth.models import User

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
                .get(profile=uid)
        except models.P3Profile.DoesNotExist:
            p3p = None
    if p3p:
        profile.update({
            'interests': [ t.name for t in p3p.interests.all() ],
            'twitter': p3p.twitter,
            'image': p3p.profile_image_url(),
            'image_gravatar': p3p.image_gravatar,
            'image_url': p3p.image_url,
            'spam_recruiting': p3p.spam_recruiting,
            'spam_user_message': p3p.spam_user_message,
            'spam_sms': p3p.spam_sms,
        })
    return profile

def _i_profile_data(sender, **kw):
    # l'invalidazione tramite segnale viene gestita da cachef
    return 'profile:%s' % (kw['instance'].profile_id,)

profile_data = cache_me(
    signals=(cdata.profile_data.invalidated,),
    models=(models.P3Profile,),
    key='profile:%(uid)s')(profile_data, _i_profile_data)

def profiles_data(uids):
    cached = zip(uids, profile_data.get_from_cache([ (x,) for x in uids ]))
    missing = [ x[0] for x in cached if x[1] is cache_me.CACHE_MISS ]

    preload = {}
    profiles = models.P3Profile.objects\
        .filter(profile__in=missing)
    for p in profiles:
        preload[p.profile_id] = {'profile': p}

    cdata.profiles_data(missing)
    output = []
    for ix, e in enumerate(cached):
        pid, val = e
        if val is cache_me.CACHE_MISS:
            val = profile_data(pid, preload=preload[pid])
        output.append(val)

    return output

def user_tickets(user, conference, only_complete=False):
    """
    Restituisce i biglietti associati all'utente (perché li ha comprati o
    perché gli sono stati assegnati).
    """
    q1 = user.ticket_set.all()\
        .conference(conference)

    q2 = cmodels.Ticket.objects\
        .filter(p3_conference__assigned_to=user.email)\
        .filter(fare__conference=conference)

    qs = (q1 | q2)\
        .select_related('orderitem__order', 'fare')
    if not only_complete:
        return qs
    else:
        # non mostro i biglietti associati ad ordini paypal che non risultano
        # ancora "completi"; poiché la notifica IPN è quasi contestuale al ritorno
        # dell'utente sul nostro sito, filtrando via gli ordini non confermati
        # elimino di fatto vecchi record rimasti nel db dopo che l'utente non ha
        # confermato il pagamento sul sito paypal o dopo che è tornato indietro
        # utilizzando il pulsante back
        tickets = list(qs)
        for ix, t in list(enumerate(tickets))[::-1]:
            order = t.orderitem.order
            if order.method not in ('bank', 'admin') and not order.complete():
                del tickets[ix]
        return tickets

def conference_users(conference):
    """
    Restituisce l'elenco degli user_id che partecipano alla conferenza.
    """
    ticket_qs = cmodels.Ticket.objects\
        .filter(fare__conference=conference)\
        .filter(fare__code__startswith='T')\
    # I biglietti non assegnati
    q1 = User.objects\
        .filter(id__in=\
            ticket_qs\
                .filter(p3_conference__assigned_to__in=(None, ''))\
                .values_list('user', flat=True)
        )\
        .values_list('id', flat=True)

    # e i biglietti assegnati
    q2 = User.objects\
        .filter(email__in=\
            ticket_qs\
                .exclude(p3_conference__assigned_to__in=(None,''))\
                .values('p3_conference__assigned_to')
        )\
        .values_list('id', flat=True)
    return q1 | q2
