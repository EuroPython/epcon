from assopy import models
from conference import cachef
from conference.models import Ticket
from django.contrib.auth.models import User
from django.urls import reverse
from django.db.models import Q

cache_me = cachef.CacheFunction(prefix='assopy:')

def user_data(u):
    return {
        'name': '%s %s' % (u.first_name, u.last_name),
        'email': u.email,
    }

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
        .filter(user__user=u)\
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
        'tickets': user_tickets(user),
        'orders': user_orders(user),
        'coupons': user_coupons(user),
    }
    return output
