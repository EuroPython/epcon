# -*- coding: UTF-8 -*-
from django import forms
from django import template
from django.conf import settings
from django.conf.urls.defaults import url, patterns
from django.contrib import admin
from django.db.models import Count
from django.shortcuts import render_to_response
from conference.admin import TicketAdmin
from conference.models import Ticket
from p3 import models

from collections import defaultdict

class TicketConferenceAdmin(TicketAdmin):
    list_display = TicketAdmin.list_display + ('_order', '_assigned',)
    list_filter = ('orderitem__order___complete', 'fare__code',)
    
    def _order(self, o):
        return o.orderitem.order.code

    def _assigned(self, o):
        if o.p3_conference:
            return o.p3_conference.assigned_to
        else:
            return ''

    def queryset(self, request):
        qs = super(TicketConferenceAdmin, self).queryset(request)
        qs = qs.select_related('orderitem__order', 'p3_conference', 'user', 'fare', )
        return qs

    def get_urls(self):
        urls = super(TicketAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^stats/$', self.admin_site.admin_view(self.stats), name='p3-ticket-stats'),
        )
        return my_urls + urls

    def stats(self, request):
        from conference.models import Conference, Ticket
        class FormConference(forms.Form):
            conference = forms.ChoiceField(
                choices=Conference.objects.all().values_list('code', 'name'),
                required=False
            )
        form = FormConference(data=request.GET)
        stats = []
        if form.is_valid():
            tickets = Ticket.objects.filter(orderitem__order___complete=True, fare__ticket_type='conference')
            compiled = tickets.exclude(p3_conference=None).exclude(name='')
            stats.append({
                'code': 'all',
                'title': 'Biglietti venduti',
                'count': tickets.count(),
            })
            stats.append({
                'code': 'not_compiled',
                'title': 'Biglietti non compilati',
                'count': (tickets.exclude(p3_conference=None).filter(name='') | tickets.filter(p3_conference=None)).count(),
            })
            stats.append({
                'code': 'compiled',
                'title': 'Biglietti compilati',
                'count': compiled.count(),
            })
            sizes = dict(models.TICKET_CONFERENCE_SHIRT_SIZES)
            for x in compiled.values('p3_conference__shirt_size').annotate(c=Count('id')):
                stats.append({
                    'code': 'tshirt_%s' % x['p3_conference__shirt_size'],
                    'title': 'Taglia maglietta: %s' % sizes.get(x['p3_conference__shirt_size']),
                    'count': x['c'], 
                })
            diets = dict(models.TICKET_CONFERENCE_DIETS)
            for x in compiled.values('p3_conference__diet').annotate(c=Count('id')):
                stats.append({
                    'code': 'diet_%s' % x['p3_conference__diet'],
                    'title': 'Dieta: %s' % diets.get(x['p3_conference__diet']),
                    'count': x['c'], 
                })
            days = defaultdict(lambda: 0)
            for x in compiled.select_related('p3_conference'):
                data = filter(None, map(lambda x: x.strip(), x.p3_conference.days.split(',')))
                if not data:
                    days['x'] += 1
                else:
                    for v in data:
                        days[v] += 1
            for day, count in days.items():
                stats.append({
                    'code': 'days_%s' % day,
                    'title': 'Giorno di presenza: %s' % day,
                    'count': count,
                })
                
        ctx = {
            'form': form,
            'stats': stats,
        }
        return render_to_response('conference/admin/ticket_stats.html', ctx, context_instance=template.RequestContext(request))

admin.site.unregister(Ticket)
admin.site.register(Ticket, TicketConferenceAdmin)

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
