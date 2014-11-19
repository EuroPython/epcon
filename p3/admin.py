# -*- coding: UTF-8 -*-
from django import forms
from django import http
from django.conf import settings
from django.conf.urls.defaults import url, patterns
from django.contrib import admin
from django.core import urlresolvers
from assopy import admin as aadmin
from assopy import models as amodels
from conference import admin as cadmin
from conference import models as cmodels
from p3 import models
from p3 import dataaccess

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
                p3c = o.p3_conference
                if p3c:
                    initial = kw.pop('initial', {})
                    for k in _TICKET_CONFERENCE_COPY_FIELDS:
                        initial[k] = getattr(p3c, k)
                    kw['initial'] = initial
            return super(TicketConferenceForm, self).__init__(*args, **kw)

    return TicketConferenceForm

class TicketConferenceAdmin(cadmin.TicketAdmin):
    list_display = cadmin.TicketAdmin.list_display + ('_order', '_assigned', '_tagline',)
    list_filter = cadmin.TicketAdmin.list_filter + ('orderitem__order___complete',)

    form = ticketConferenceForm()

    class Media:
        js = ('p5/j/jquery-flot/jquery.flot.js',)

    def _order(self, o):
        return o.orderitem.order.code

    def _assigned(self, o):
        if o.p3_conference:
            return o.p3_conference.assigned_to
        else:
            return ''

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
        p3c = obj.p3_conference
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

from conference import forms as cforms

class TalkConferenceAdminForm(cadmin.TalkAdminForm):
    def __init__(self, *args, **kwargs):
        super(TalkConferenceAdminForm, self).__init__(*args, **kwargs)
        self.fields['tags'].required = False

class TalkConferenceAdmin(cadmin.TalkAdmin):
    multilingual_widget = cforms.MarkEditWidget
    form = TalkConferenceAdminForm

admin.site.unregister(cmodels.Talk)
admin.site.register(cmodels.Talk, TalkConferenceAdmin)

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

class HotelRoomAdmin(admin.ModelAdmin):
    list_display = ('conference', 'room_type', 'quantity', 'amount',)
    list_editable = ('quantity', 'amount',)
    list_filter = ('conference',)

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
