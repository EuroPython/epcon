# -*- coding: UTF-8 -*-
from django import forms
from django import http
from django import template
from django.conf import settings
from django.conf.urls.defaults import url, patterns
from django.contrib import admin
from django.core import mail
from django.core.urlresolvers import reverse
from django.db.models import Count, Q
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
        urls = super(TicketConferenceAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^stats/details/$', self.admin_site.admin_view(self.stats_details), name='p3-ticket-stats-details'),
            url(r'^stats/details/csv$', self.admin_site.admin_view(self.stats_details_csv), name='p3-ticket-stats-details-csv'),
        )
        return my_urls + urls

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
                    try:
                        p3c = ticket.p3_conference
                    except models.TicketConference.DoesNotExist:
                        p3c = None
                    if p3c and p3c.assigned_to:
                        emails[p3c.assigned_to] = User.objects.get(user__email=p3c.assigned_to)
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
            try:
                p3c = ticket.p3_conference
            except models.TicketConference.DoesNotExist:
                p3c = None
            row = {
                'attendee': ticket.name,
                'attendee_email': p3c.assigned_to if p3c else '',
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
