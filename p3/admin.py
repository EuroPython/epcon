# -*- coding: UTF-8 -*-
from django import forms
from django import http
from django import template
from django.conf import settings
from django.conf.urls.defaults import url, patterns
from django.contrib import admin
from django.core import mail
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.shortcuts import render_to_response, redirect
from conference.admin import TicketAdmin
from conference.models import Ticket
from p3 import models

import csv
from collections import defaultdict
from cStringIO import StringIO

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
            url(r'^stats/$', self.admin_site.admin_view(self.stats_list), name='p3-ticket-stats'),
            url(r'^stats/details/$', self.admin_site.admin_view(self.stats_details), name='p3-ticket-stats-details'),
            url(r'^stats/details/csv$', self.admin_site.admin_view(self.stats_details_csv), name='p3-ticket-stats-details-csv'),
        )
        return my_urls + urls

    def stats(self, conference, stat=None):
        stats = []
        tickets = Ticket.objects.filter(
            orderitem__order___complete=True,
            fare__ticket_type='conference',
            fare__conference=conference,
        ).select_related('p3_conference', 'orderitem__order__user__user')
        compiled = tickets.exclude(p3_conference=None).exclude(name='')
        not_compiled = tickets.exclude(p3_conference=None).filter(name='') | tickets.filter(p3_conference=None)
        if stat in (None, 'all'):
            stats.append({
                'code': 'all',
                'title': 'Biglietti venduti',
                'count': tickets.count(),
                'have_details': True,
                'details': tickets,
            })
        if stat in (None, 'not_compiled'):
            stats.append({
                'code': 'not_compiled',
                'title': 'Biglietti non compilati',
                'count': not_compiled.count(),
                'have_details': True,
                'details': not_compiled,
            })
        if stat in (None, 'compiled'):
            stats.append({
                'code': 'compiled',
                'title': 'Biglietti compilati',
                'count': compiled.count(),
                'have_details': True,
                'details': compiled,
            })
        if stat is None or stat.startswith('tshirt_'):
            sizes = dict(models.TICKET_CONFERENCE_SHIRT_SIZES)
            for x in compiled.values('p3_conference__shirt_size').annotate(c=Count('id')):
                scode = 'tshirt_%s' % x['p3_conference__shirt_size']
                if stat in (None, scode):
                    stats.append({
                        'code': scode,
                        'title': 'Taglia maglietta: %s' % sizes.get(x['p3_conference__shirt_size']),
                        'count': x['c'], 
                        'have_details': True,
                        'details': compiled.filter(p3_conference__shirt_size=x['p3_conference__shirt_size']),
                    })
        if stat is None or stat.startswith('diet_'):
            diets = dict(models.TICKET_CONFERENCE_DIETS)
            for x in compiled.values('p3_conference__diet').annotate(c=Count('id')):
                scode = 'diet_%s' % x['p3_conference__diet']
                if stat in (None, scode):
                    stats.append({
                        'code': scode,
                        'title': 'Dieta: %s' % diets.get(x['p3_conference__diet']),
                        'count': x['c'], 
                        'have_details': True,
                        'details': compiled.filter(p3_conference__diet=x['p3_conference__diet']),
                    })
        if stat is None or stat.startswith('days_'):
            days = defaultdict(lambda: 0)
            for x in compiled:
                data = filter(None, map(lambda x: x.strip(), x.p3_conference.days.split(',')))
                if not data:
                    days['x'] += 1
                else:
                    for v in data:
                        days[v] += 1
            for day, count in days.items():
                scode = 'days_%s' % day
                if stat in (None, scode):
                    stats.append({
                        'code': scode,
                        'title': 'Giorno di presenza: %s' % day,
                        'count': count,
                        'have_details': False,
                    })
        return stats

    def stats_list(self, request):
        from conference.models import Conference, Ticket
        class FormConference(forms.Form):
            conference = forms.ChoiceField(
                choices=Conference.objects.all().values_list('code', 'name'),
                required=False
            )
        form = FormConference(data=request.GET)
        stats = []
        if form.is_valid():
            conference = form.cleaned_data['conference'] or settings.CONFERENCE_CONFERENCE
            stats = self.stats(conference)
        else:
            stats = []

        ctx = {
            'form': form,
            'conference': conference,
            'stats': stats,
        }
        return render_to_response('conference/admin/ticket_stats.html', ctx, context_instance=template.RequestContext(request))

    def stats_details(self, request):
        code = request.GET['code']
        conference = request.GET['conference']
        stats = self.stats(conference, stat=code)
        if not stats:
            raise http.Http404()

        class SendMailForm(forms.Form):
            from_ = forms.EmailField(max_length=50, initial=settings.DEFAULT_FROM_EMAIL)
            subject = forms.CharField(max_length=200)
            body = forms.CharField(widget=forms.Textarea)

        if request.method == "POST":
            from assopy.models import User
            from django.template import Template, Context

            form = SendMailForm(data=request.POST)
            if form.is_valid():
                data = form.cleaned_data
                tSubject = Template(data['subject'])
                tBody = Template(data['body'])

                emails = {}
                for ticket in stats[0]['details']:
                    if ticket.p3_conference and ticket.p3_conference.assigned_to:
                        emails[ticket.p3_conference.assigned_to] = User.objects.get(user__email=ticket.p3_conference.assigned_to)
                    else:
                        emails[ticket.orderitem.order.user.user.email] = ticket.orderitem.order.user
                messages = []
                for email, user in emails.items():
                    ctx = Context({
                        'user': user,
                    })
                    messages.append((
                        tSubject.render(ctx),
                        tBody.render(ctx),
                        data['from_'],
                        [ email ]
                    ))
                mail.send_mass_mail(messages)
                ctx = dict(form.cleaned_data)
                ctx['addresses'] = '\n'.join('%s - %s' % (k, v.name()) for k, v in emails.items())
                mail.send_mail(
                    'feedback mail',
                    '''
message sent
-------------------------------
FROM: %(from_)s
SUBJECT: %(subject)s
BODY:
%(body)s
-------------------------------
sent to:
%(addresses)s
                    ''' % ctx,
                    settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[request.user.email],

                )
                u = reverse('admin:p3-ticket-stats-details') + '?conference=%s&code=%s' % (conference, code)
                return redirect(u)
        else:
            form = SendMailForm()
        ctx = {
            'conference': conference,
            'stat': stats[0],
            'form': form,
        }
        return render_to_response('conference/admin/ticket_stats_details.html', ctx, context_instance=template.RequestContext(request))

    def stats_details_csv(self, request):
        code = request.GET['code']
        conference = request.GET['conference']
        stats = self.stats(conference, stat=code)
        if not stats:
            raise http.Http404()
        columns = (
            'attendee', 'attendee_email',
            'buyer', 'buyer_email',
            'order',
        )
        buff = StringIO()
        writer = csv.DictWriter(buff, columns)
        writer.writerow(dict(zip(columns, columns)))
        for ticket in stats[0]['details']:
            row = {
                'attendee': ticket.name,
                'attendee_email': ticket.p3_conference.assigned_to if ticket.p3_conference else '',
                'buyer': ticket.orderitem.order.user.name(),
                'buyer_email': ticket.orderitem.order.user.user.email,
                'order': ticket.orderitem.order.code,
            }
            for k, v in row.items():
                try:
                    row[k] = v.encode('utf-8')
                except:
                    pass
            writer.writerow(row)
        return http.HttpResponse(buff.getvalue(), mimetype="text/csv")

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
