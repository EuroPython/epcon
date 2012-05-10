# -*- coding: UTF-8 -*-
from assopy import models
from conference import cachef
from conference.models import Ticket
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Q

cache_me = cachef.CacheFunction(prefix='assopy:')

def user_data(u):
    return {
        'name': '%s %s' % (u.first_name, u.last_name),
        'email': u.email,
    }

def user_identities(u):
    return [{
        'provider': i.provider,
        'identifier': i.identifier,
        } for i in u.assopy_user.identities.all()]
        
def user_tickets(u):
    qs = Ticket.objects\
        .filter(user=u)\
        .order_by('-fare__conference')\
        .select_related('fare')

    def order(t):
        try:
            o = models.Order.objects\
                .get(orderitem__ticket=t)
        except models.Order.DoesNotExist:
            return {}
        return {
            'code': o.code,
            'created': o.created,
            'url': reverse('admin:assopy_order_change', args=(o.id,)),
        }
    return [{
            'id': t.id,
            'type': t.ticket_type,
            'fare': {
                'code': t.fare.code,
                'conference': t.fare.conference,
                'recipient': t.fare.recipient_type,
            },
            'note': '',
            'order': order(t),
        } for t in qs]

def user_orders(u):
    qs = u.assopy_user.orders.all().order_by('-created')
    return [{
        'code': o.code,
        'created': o.created,
        'method': o.method,
        'complete': o._complete,
        'billing': {
            'address': o.address,
            'notes': o.billing_notes,
        },
        'total': {
            'gross': o.total(apply_discounts=False),
            'net': o.total(),
        },
        'url': reverse('admin:assopy_order_change', args=(o.id,)),
        } for o in qs]

def user_coupons(u):
    assigned_coupon = models.Coupon.objects\
        .filter(user=u)\
        .values('code')
    user_coupon = models.OrderItem.objects\
        .filter(price__lt=0, order__user__user=u)\
        .values('code')

    qs = models.Coupon.objects\
        .filter(Q(code__in=assigned_coupon)|Q(code__in=user_coupon))\
        .order_by('-conference__code')
    def orders(c):
        return models.Order.objects\
            .filter(orderitem__code=c.code, created__year=c.conference.conference_start.year)\
            .order_by('-created')
    return [{
        'code': c.code,
        'conference': c.conference.code,
        'value': c.value,
        'valid': c.valid(),
        'url': reverse('admin:assopy_coupon_change', args=(c.id,)),
        'orders': [{
            'code': o.code,
            'created': o.created,
            'url': reverse('admin:assopy_order_change', args=(o.id,)),
            } for o in orders(c)],
        } for c in qs]

def all_user_data(uid):
    """
    Aggrega le informazioni disponibili su un utente:
        * dati anagrafici
        * identità collegate
        * biglietti
        * ordini
        * coupon
    """
    user = User.objects.get(id=uid)
    output = {
        'user': user_data(user),
        'identities': user_identities(user),
        'tickets': user_tickets(user),
        'orders': user_orders(user),
        'coupons': user_coupons(user),
    }
    return output

# XXX: per il momento all_user_data viene usata solo dall'admin, quindi non è
# oggetto di richieste parallele; se le perfomance dovessero essere troppo
# oscene bisognerà ricorrere alla cache.

#def _i_all_user_data(sender, **kw):
#    if sender is User:
#        uids = [ kw['instance'].id ]
#    elif sender is models.UserIdentity:
#        uids = [ kw['instance'].user.user_id ]
#    elif sender is models.Order:
#        uids = [ kw['instance'].user.user_id ]
#    elif sender is models.Coupon:
#        uids = []
#        if kw['instance'].user:
#            uids.append(kw['instance'].user.user_id)
#        uids.extend(models.Order.objects\
#            .filter(
#                orderitem__code=kw['instance'].code,
#                created__year=kw['instance'].conference.conference_start.year)\
#            .values_list('user__user', flat=True))
#    elif sender is Ticket:
#        uids = [ kw['instance'].user_id ]
#
#    return [ 'all_user_data:%s' % x for x in uids ]
#
#all_user_data = cache_me(
#    models=(User, models.UserIdentity, models.Order, models.Coupon, Ticket),
#    key='all_user_data:%(uid)s')(all_user_data, _i_all_user_data)
