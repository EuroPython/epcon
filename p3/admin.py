# -*- coding: UTF-8 -*-
from collections import defaultdict
from decimal import Decimal
from django import forms
from django import http
from django.conf import settings
from django.conf.urls import url, patterns
from django.contrib import admin
from django.core import urlresolvers
from django.db.models import Q
from django.contrib.auth.models import User
from assopy import admin as aadmin
from assopy import models as amodels
from assopy import stats as astats
from assopy import utils as autils
from conference import admin as cadmin
from conference import models as cmodels
from conference import forms as cforms
from p3 import models
from p3 import dataaccess
from p3 import utils

### Customg list filters

class DiscountListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'discounts'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'discounts'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'With discounts'),
            ('no', 'Regular order'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(orderitem__price__lt=0)
        elif self.value() == 'no':
            return queryset.exclude(orderitem__price__lt=0)

###

_TICKET_CONFERENCE_COPY_FIELDS = ('shirt_size', 'python_experience', 'diet', 'tagline', 'days', 'badge_image')
def ticketConferenceForm():
    class _(forms.ModelForm):
        class Meta:
            model = models.TicketConference
    fields = _().fields

    class TicketConferenceForm(forms.ModelForm):
        shirt_size = fields['shirt_size']
        python_experience = fields['python_experience']
        diet = fields['diet']
        tagline = fields['tagline']
        days = fields['days']
        badge_image = fields['badge_image']

        class Meta:
            model = cmodels.Ticket

        def __init__(self, *args, **kw):
            if 'instance' in kw:
                o = kw['instance']
                try:
                    p3c = o.p3_conference
                except models.TicketConference.DoesNotExist:
                    pass
                else:
                    if p3c:
                        initial = kw.pop('initial', {})
                        for k in _TICKET_CONFERENCE_COPY_FIELDS:
                            initial[k] = getattr(p3c, k)
                        kw['initial'] = initial
            return super(TicketConferenceForm, self).__init__(*args, **kw)

    return TicketConferenceForm

class TicketConferenceAdmin(cadmin.TicketAdmin):
    list_display = cadmin.TicketAdmin.list_display + (
        '_order',
        '_order_date',
        '_assigned',
        '_shirt_size',
        '_diet',
        '_python_experience',
        #'_tagline',
        )
    list_select_related = True
    list_filter = cadmin.TicketAdmin.list_filter + (
        'fare__code',
        'orderitem__order___complete',
        'p3_conference__shirt_size',
        'p3_conference__diet',
        'p3_conference__python_experience',
        'orderitem__order__created',
        )
    search_fields = cadmin.TicketAdmin.search_fields + (
        'orderitem__order__code',
        'fare__code',
        )
    actions = cadmin.TicketAdmin.actions + (
        'do_assign_to_buyer',
        )
    form = ticketConferenceForm()

    class Media:
        js = ('p5/j/jquery-flot/jquery.flot.js',)

    def _order(self, obj):
        url = urlresolvers.reverse('admin:assopy_order_change', args=(obj.orderitem.order.id,))
        return '<a href="%s">%s</a>' % (url, obj.orderitem.order.code)
    _order.allow_tags = True

    def _order_date(self, o):
        return o.orderitem.order.created
    _order_date.admin_order_field = 'orderitem__order__created'

    def _assigned(self, o):
        if o.p3_conference:
            assigned_to = o.p3_conference.assigned_to
            if assigned_to:
                try:
                    user = autils.get_user_account_from_email(assigned_to)
                except User.MultipleObjectsReturned:
                    if user.email == assigned_to:
                        # Use the buyer user account
                        user = o.user
                    else:
                        return '%s (email not unique)' % assigned_to
                if user:
                    url = urlresolvers.reverse('admin:auth_user_change',
                                               args=(user.id,))
                    return '<a href="%s">%s</a>' % (url, assigned_to)
            return assigned_to
        else:
            return ''
    _assigned.allow_tags = True
    _assigned.admin_order_field = 'p3_conference__assigned_to'

    def do_assign_to_buyer(self, request, queryset):

        if not queryset:
            self.message_user('no tickets selected')
            return
        for ticket in queryset:
            # Assign to buyer
            utils.assign_ticket_to_user(ticket, ticket.user)

    do_assign_to_buyer.short_description = 'Assign to buyer'

    def _shirt_size(self, o):
        try:
            p3c = o.p3_conference
        except models.TicketConference.DoesNotExist:
            return ''
        return p3c.shirt_size

    def _diet(self, o):
        try:
            p3c = o.p3_conference
        except models.TicketConference.DoesNotExist:
            return ''
        return p3c.diet

    def _python_experience(self, o):
        try:
            p3c = o.p3_conference
        except models.TicketConference.DoesNotExist:
            return ''
        return p3c.python_experience
    _python_experience.admin_order_field = 'p3_conference__python_experience'

    def _tagline(self, o):
        try:
            p3c = o.p3_conference
        except models.TicketConference.DoesNotExist:
            return ''
        html = p3c.tagline
        if p3c.badge_image:
            i = ['<img src="%s" width="24" />' % p3c.badge_image.url] * p3c.python_experience
            html += '<br />' + ' '.join(i)
        return html
    _tagline.allow_tags = True

    def save_model(self, request, obj, form, change):
        obj.save()
        try:
            p3c = obj.p3_conference
        except models.TicketConference.DoesNotExist:
            p3c = None
        if p3c is None:
            p3c = models.TicketConference(ticket=obj)

        data = form.cleaned_data
        for k in _TICKET_CONFERENCE_COPY_FIELDS:
            setattr(p3c, k, data.get(k))
        p3c.save()

    def changelist_view(self, request, extra_context=None):
        if not request.GET:
            q = request.GET.copy()
            q['fare__conference'] = settings.CONFERENCE_CONFERENCE
            q['fare__ticket_type__exact'] = 'conference'
            q['orderitem__order___complete__exact'] = 1
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(TicketConferenceAdmin,self).changelist_view(request, extra_context=extra_context)

    def queryset(self, request):
        qs = super(TicketConferenceAdmin, self).queryset(request)
        qs = qs.select_related('orderitem__order', 'p3_conference', 'user', 'fare', )
        return qs

    def get_urls(self):
        urls = super(TicketConferenceAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^stats/data/$', self.admin_site.admin_view(self.stats_data), name='p3-ticket-stats-data'),
        )
        return my_urls + urls

    def stats_data(self, request):
        from conference.views import json_dumps
        from django.db.models import Q
        from collections import defaultdict
        from microblog.models import PostContent
        import datetime

        conferences = cmodels.Conference.objects\
            .order_by('conference_start')

        output = {}
        for c in conferences:
            tickets = cmodels.Ticket.objects\
                .filter(fare__conference=c)\
                .filter(Q(orderitem__order___complete=True) | Q(orderitem__order__method__in=('bank', 'admin')))\
                .select_related('fare', 'orderitem__order')
            data = {
                'conference': defaultdict(lambda: 0),
                'partner': defaultdict(lambda: 0),
                'event': defaultdict(lambda: 0),
                'other': defaultdict(lambda: 0),
            }
            for t in tickets:
                tt = t.fare.ticket_type
                date = t.orderitem.order.created.date()
                offset = date - c.conference_start
                data[tt][offset.days] += 1

            for k, v in data.items():
                data[k] = sorted(v.items())


            dlimit = datetime.date(c.conference_start.year, 1, 1)
            deadlines = cmodels.DeadlineContent.objects\
                .filter(language='en')\
                .filter(deadline__date__lte=c.conference_start, deadline__date__gte=dlimit)\
                .select_related('deadline')\
                .order_by('deadline__date')
            markers = [ ((d.deadline.date - c.conference_start).days, 'CAL: ' + (d.headline or d.body)) for d in deadlines ]

            posts = PostContent.objects\
                .filter(language='en')\
                .filter(post__date__lte=c.conference_start, post__date__gte=dlimit)\
                .filter(post__status='P')\
                .select_related('post')\
                .order_by('post__date')
            markers += [ ((d.post.date.date() - c.conference_start).days, 'BLOG: ' + d.headline) for d in posts ]

            output[c.code] = {
                'data': data,
                'markers': markers,
            }

        return http.HttpResponse(json_dumps(output), 'text/javascript')

admin.site.unregister(cmodels.Ticket)
admin.site.register(cmodels.Ticket, TicketConferenceAdmin)

class SpeakerAdmin(cadmin.SpeakerAdmin):

    list_display = cadmin.SpeakerAdmin.list_display + (
        )
    list_filter = (
        'p3_speaker__first_time',
        )

    def queryset(self, request):
        # XXX: waiting to upgrade to django 1.4, I'm implementing
        # this bad hack filter to keep only speakers of current conference.
        qs = super(SpeakerAdmin, self).queryset(request)
        qs = qs.filter(user__in=(
            cmodels.TalkSpeaker.objects\
                .filter(talk__conference=settings.CONFERENCE_CONFERENCE)\
                .values('speaker')
        ))
        return qs

    def get_paginator(self, request, queryset, per_page, orphans=0, allow_empty_first_page=True):
        sids = queryset.values_list('user', flat=True)
        profiles = dataaccess.profiles_data(sids)
        self._profiles = dict(zip(sids, profiles))
        return super(SpeakerAdmin, self).get_paginator(request, queryset, per_page, orphans, allow_empty_first_page)

    def _avatar(self, o):
        return '<img src="%s" height="32" />' % (self._profiles[o.user_id]['image'],)
    _avatar.allow_tags = True

admin.site.unregister(cmodels.Speaker)
admin.site.register(cmodels.Speaker, SpeakerAdmin)

class DonationAdmin(admin.ModelAdmin):
    list_display = ('_name', 'date', 'amount')
    list_select_related = True
    search_fields = ('user__user__first_name', 'user__user__last_name', 'user__user__email')
    date_hierarchy = 'date'

    def _name(self, o):
        return o.user.name()
    _name.short_description = 'name'
    _name.admin_order_field = 'user__user__first_name'

admin.site.register(models.Donation, DonationAdmin)

class HotelBookingAdmin(admin.ModelAdmin):
    list_display = ('conference', 'booking_start', 'booking_end', 'minimum_night')

admin.site.register(models.HotelBooking, HotelBookingAdmin)

class HotelRoomAdmin(admin.ModelAdmin):
    list_display = ('_conference', 'room_type', 'quantity', 'amount',)
    list_editable = ('quantity', 'amount',)
    list_filter = ('booking__conference',)
    list_select_related = True

    def _conference(self, o):
        return o.booking.conference_id

    def get_urls(self):
        urls = super(HotelRoomAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^tickets/$', self.admin_site.admin_view(self.ticket_list), name='p3-hotelrooms-tickets-data'),
        )
        return my_urls + urls

    def ticket_list(self, request):
        from conference.views import json_dumps
        day_ix = int(request.GET['day'])
        room_type = request.GET['type']
        rdays = models.TicketRoom.objects.reserved_days()
        day = rdays[day_ix]

        qs = models.TicketRoom.objects.valid_tickets()\
            .filter(room_type__room_type=room_type, checkin__lte=day, checkout__gte=day)\
            .select_related('ticket__user', 'ticket__orderitem__order')\
            .order_by('ticket__orderitem__order__created')

        output = []
        for row in qs:
            user = row.ticket.user
            order = row.ticket.orderitem.order
            name = u'{0} {1}'.format(user.first_name, user.last_name)
            if row.ticket.name and row.ticket.name != name:
                name = u'{0} ({1})'.format(row.ticket.name, name)
            output.append({
                'user': {
                    'id': user.id,
                    'name': name,
                },
                'order': {
                    'id': order.id,
                    'code': order.code,
                    'method': order.method,
                    'complete': order._complete,
                },
                'period': (row.checkin, row.checkout, row.checkout == day),
            })
        return http.HttpResponse(json_dumps(output), 'text/javascript')

admin.site.register(models.HotelRoom, HotelRoomAdmin)

class TicketRoomAdmin(admin.ModelAdmin):
    list_display = ('_user', '_room_type', 'ticket_type', 'checkin', 'checkout', '_order_code', '_order_date', '_order_confirmed')
    list_select_related = True
    search_fields = ('ticket__user__first_name', 'ticket__user__last_name', 'ticket__user__email', 'ticket__orderitem__order__code')
    raw_id_fields = ('ticket', )
    list_filter = ('room_type__room_type',)

    def _user(self, o):
        return o.ticket.user

    def _room_type(self, o):
        return o.room_type.get_room_type_display()

    def _order_code(self, o):
        return o.ticket.orderitem.order.code

    def _order_date(self, o):
        return o.ticket.orderitem.order.created

    def _order_confirmed(self, o):
        return o.ticket.orderitem.order._complete
    _order_confirmed.boolean = True

admin.site.register(models.TicketRoom, TicketRoomAdmin)

class InvoiceAdmin(aadmin.InvoiceAdmin):
    """
    Specializzazione per gestire il download delle fatture generate con genro
    """

    def _invoice(self, i):
        if i.assopy_id:
            fake = not i.payment_date
            view = urlresolvers.reverse('genro-legacy-invoice', kwargs={'assopy_id': i.assopy_id})
            return '<a href="%s">View</a> %s' % (view, '[Not payed]' if fake else '')
        else:
            return super(InvoiceAdmin, self)._invoice(i)
    _invoice.allow_tags = True
    _invoice.short_description = 'Download'

admin.site.unregister(amodels.Invoice)
admin.site.register(amodels.Invoice, InvoiceAdmin)

class VotoTalkAdmin(admin.ModelAdmin):
    list_display = ('user', 'talk', 'vote')
    list_filter = ('talk__conference',
                   )
    search_fields = [ 'talk__title',
                      'user__username',
                      'user__last_name', 'user__first_name' ]

admin.site.register(cmodels.VotoTalk, VotoTalkAdmin)

class AttendeeProfileAdmin(admin.ModelAdmin):
    list_display = ('_name',
                    '_user',
                    'company', 'location', 'visibility')
    list_filter = ('visibility',
                   )
    search_fields = [ 'user__username',
                      'user__last_name', 'user__first_name',
                      'company',
                      'location',
                      ]

    def _name(self, o):
        url = urlresolvers.reverse('conference-profile',
                                   kwargs={'slug': o.slug})
        return '<a href="%s">%s %s</a>' % (url, o.user.first_name, o.user.last_name)
    _name.allow_tags = True
    _name.admin_order_field = 'user__first_name'

    def _user(self, o):
        url = urlresolvers.reverse('admin:auth_user_change',
                                   args=(o.user.id,))
        return '<a href="%s">%s</a>' % (url, o.user.username)
    _user.allow_tags = True
    _user.admin_order_field = 'user__username'


admin.site.register(cmodels.AttendeeProfile, AttendeeProfileAdmin)

# MAL: Commented out, since we don't really have a need for this:
#
# class TalkConferenceAdminForm(cadmin.TalkAdminForm):
#     def __init__(self, *args, **kwargs):
#         super(TalkConferenceAdminForm, self).__init__(*args, **kwargs)
#         self.fields['tags'].required = False
#
# class TalkConferenceAdmin(cadmin.TalkAdmin):
#     multilingual_widget = cforms.MarkEditWidget
#     form = TalkConferenceAdminForm
#
# admin.site.unregister(cmodels.Talk)
# admin.site.register(cmodels.Talk, TalkConferenceAdmin)

class TalkAdmin(cadmin.TalkAdmin):
    list_filter = ('conference', 'status', 'duration', 'type',
                   'level', 'tags__name', 'language',
                   )
    search_fields = [ 'title',
                      'talkspeaker__speaker__user__last_name',
                      'talkspeaker__speaker__user__first_name',
                      'speakers__user__attendeeprofile__company',
                      ]

    list_display = ('title', 'conference', '_speakers',
                    '_company',
                    'duration', 'status', 'created',
                    'level', '_tags',
                    '_slides', '_video',
                    'language',
                    )

    ordering = ('-conference', 'title')
    multilingual_widget = cforms.MarkEditWidget

    def _tags(self, obj):
        return u', '.join(sorted(unicode(tag) for tag in obj.tags.all()))

    def _company(self, obj):
        companies = sorted(
            set(speaker.user.attendeeprofile.company
                for speaker in obj.speakers.all()
                if speaker.user.attendeeprofile))
        return u', '.join(companies)
    _company.admin_order_field = 'speakers__user__attendeeprofile__company'

admin.site.unregister(cmodels.Talk)
admin.site.register(cmodels.Talk, TalkAdmin)

class OrderAdmin(aadmin.OrderAdmin):
    list_display = aadmin.OrderAdmin.list_display + (
        'country',
        )
    list_filter = aadmin.OrderAdmin.list_filter + (
        DiscountListFilter,
        'country',
        )

admin.site.unregister(amodels.Order)
admin.site.register(amodels.Order, OrderAdmin)

class EventTrackInlineAdmin(admin.TabularInline):
    model = cmodels.EventTrack
    extra = 3

class EventAdmin(admin.ModelAdmin):
    list_display = ('schedule',
                    'start_time',
                    'duration',
                    '_title',
                    '_tracks')
    ordering = ('schedule',
                'start_time',
                'tracks',
                )
    list_filter = ('schedule',
                   'tracks')
    search_fields = ['talk__title',
                     'custom',
                     ]
    inlines = (EventTrackInlineAdmin,
               )

    def _tracks(self, obj):
        return ", ".join([track.track
                          for track in obj.tracks.all()])

    def _title(self, obj):
        if obj.custom:
            return obj.custom
        else:
            return obj.talk

admin.site.register(cmodels.Event, EventAdmin)

class TrackAdmin(admin.ModelAdmin):
    list_display = ('schedule',
                    '_slug',
                    '_date',
                    'track',
                    'title',
                    )
    ordering = ('schedule',
                'track',
                )
    list_filter = ('schedule',
                   'schedule__slug',
                   'track',
                   'title')
    search_fields = ['schedule__conference',
                     'schedule__slug',
                     'track',
                     'title',
                     ]
    inlines = (EventTrackInlineAdmin,
               )
    list_select_related = True

    def _slug(self, obj):
        return obj.schedule.slug

    def _date(self, obj):
        return obj.schedule.date

admin.site.register(cmodels.Track, TrackAdmin)

class ScheduleAdmin(cadmin.ScheduleAdmin):
    pass

admin.site.unregister(cmodels.Schedule)
admin.site.register(cmodels.Schedule, ScheduleAdmin)

### Orders Stats

# For simplicity, we monkey patch the
# assopy.stats.prezzo_biglietti_ricalcolato() function here.
#
# This is poor style, but until we have merged the packages into the
# epcon package, this is the easiest way forward.

def prezzo_biglietti_ricalcolato(**kw):
    """
    Ricalcola il ricavo dei biglietti eliminando quelli gratuiti e
    ridistribuendo il prezzo sui rimanenti.
    """
    # mi interessano solo gli ordini che riguardano acquisti di biglietti
    # "conferenza"
    orders = amodels.Order.objects\
        .filter(id__in=astats._orders(**kw))\
        .values('id')\
        .distinct()
    fares = set(cmodels.Fare.objects\
        .values_list('code', flat=True))

    def _calc_prices(order_id, items):
        """
        Elimina gli item degli sconti e riduce in maniera proporzionale
        il valore dei restanti.
        """
        prices = set()
        discount = Decimal('0')
        total = Decimal('0')
        for item in items:
            if item['price'] > 0:
                prices.add(item['price'])
                total += item['price']
            else:
                discount += item['price'] * -1

        for ix, item in reversed(list(enumerate(items))):
            if item['price'] > 0:
                item['price'] = item['price'] * (total - discount) / total
            else:
                del items[ix]

    grouped = defaultdict(list)
    for ticket_type, ticket_type_description in cmodels.FARE_TICKET_TYPES:
        qs = amodels.OrderItem.objects\
            .filter(Q(ticket__isnull=True) |
                    Q(ticket__fare__ticket_type=ticket_type),
                    order__in=orders)\
            .values_list('ticket__fare__code',
                         'ticket__fare__name',
                         'price',
                         'order')
        for fcode, fname, price, oid in qs:
            if fcode in fares or price < 0:
                grouped[oid].append({
                    'code': fcode,
                    'name': fname,
                    'price': price,
                })
    for oid, items in grouped.items():
        _calc_prices(oid, items)

    # dopo l'utilizzo di _calc_prices ottengo dei prezzi che non trovo
    # più tra le tariffe ordinarie, raggruppo gli OrderItem risultanti
    # per codice tariffa e nuovo prezzo
    tcp = {}
    for rows in grouped.values():
        for item in rows:
            code = item['code']
            if code not in tcp:
                tcp[code] = {
                    'code': code,
                    'name': item['name'],
                    'prices': {}
                }
            price = item['price']
            if price not in tcp[code]['prices']:
                tcp[code]['prices'][price] = { 'price': price, 'count': 0 }
            tcp[code]['prices'][price]['count'] += 1
    return tcp.values()
prezzo_biglietti_ricalcolato.template = '''
<table>
    <tr>
        <th>Code</th>
        <th>Qty</th>
        <th style="width: 70px;">Price</th>
    </tr>
    {% for ticket in data %}
        {% for p in ticket.prices.values %}
        <tr>
            {% if forloop.counter == 1 %}
            <td title="{{ ticket.name }}" rowspan="{{ ticket.prices|length }}">{{ ticket.code }}</td>
            {% endif %}
            <td>{{ p.count }}</td>
            <td>€ {{ p.price|floatformat:"2" }}</td>
        </tr>
        {% endfor %}
    {% endfor %}
</table>
'''

# Monkey patch our version into assopy package:
if 0:
    astats.prezzo_biglietti_ricalcolato = prezzo_biglietti_ricalcolato
