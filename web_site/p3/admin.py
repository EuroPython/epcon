# -*- coding: UTF-8 -*-
from django import forms
from django import http
from django import template
from django.conf import settings
from django.conf.urls.defaults import url, patterns
from django.contrib import admin
from django.core import mail
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, redirect
from conference import admin as cadmin
from conference import models as cmodels
from p3 import models
from p3 import dataaccess

import csv
from cStringIO import StringIO

class TicketConferenceAdmin(cadmin.TicketAdmin):
    list_display = cadmin.TicketAdmin.list_display + ('_order', '_assigned', '_tagline',)
    list_filter = cadmin.TicketAdmin.list_filter + ('orderitem__order___complete',)

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
        if o.p3_conference:
            return o.p3_conference.tagline
        else:
            return ''

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
            #url(r'^stats/details/$', self.admin_site.admin_view(self.stats_details), name='p3-ticket-stats-details'),
            #url(r'^stats/details/csv$', self.admin_site.admin_view(self.stats_details_csv), name='p3-ticket-stats-details-csv'),
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

    def _stats_details(self, request):
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

admin.site.unregister(cmodels.Ticket)
admin.site.register(cmodels.Ticket, TicketConferenceAdmin)

class SpeakerAdmin(cadmin.SpeakerAdmin):
    def queryset(self, request):
        # XXX: in attesa di passare a django 1.4 implemento in questo modo
        # barbaro un filtro per limitare gli speaker a quelli della conferenza
        # in corso
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

admin.site.register(models.HotelRoom, HotelRoomAdmin)

class TicketRoomAdmin(admin.ModelAdmin):
    list_display = ('_user', '_room_type', 'ticket_type', 'checkin', 'checkout', '_order_date', '_order_confirmed')
    list_select_related = True

    def _user(self, o):
        return o.ticket.user

    def _room_type(self, o):
        return o.room_type.get_room_type_display()

    def _order_date(self, o):
        return o.ticket.orderitem.order.created

    def _order_confirmed(self, o):
        return o.ticket.orderitem.order._complete
    _order_confirmed.boolean = True

admin.site.register(models.TicketRoom, TicketRoomAdmin)

