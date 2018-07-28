# -*- coding: UTF-8 -*-
from __future__ import absolute_import

from django import forms
from django import http
from django import template
from django.contrib import admin
from django.conf import settings as dsettings
from django.conf.urls import url, patterns
from django.core import urlresolvers
from django.shortcuts import redirect, render_to_response, get_object_or_404

import common.decorators
from common.jsonify import json_dumps
from conference import dataaccess
from conference import models
from conference import settings
from conference import utils

from conference.fares import (
    FARE_CODE_TYPES,
    FARE_CODE_VARIANTS,
    FARE_CODE_GROUPS,
    FARE_CODE_REGEXES,
)


import csv
import logging
import re
from collections import defaultdict
from cStringIO import StringIO

log = logging.getLogger('conference')

class ConferenceAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', '_schedule_view', '_attendee_stats')

    def _schedule_view(self, o):
        u = urlresolvers.reverse('admin:conference-conference-schedule', args=(o.code,))
        return '<a href="%s">schedule</a>' % u
    _schedule_view.allow_tags = True

    def _attendee_stats(self, o):
        u = urlresolvers.reverse('admin:conference-ticket-stats', args=(o.code,))
        return '<a href="%s">Attendee Stats</a>' % u
    _attendee_stats.allow_tags = True

    def get_urls(self):
        v = self.admin_site.admin_view
        urls = patterns('',
            url(r'^(?P<cid>[\w-]+)/schedule/$',
                v(self.schedule_view),
                name='conference-conference-schedule'),
            url(r'^(?P<cid>[\w-]+)/schedule/(?P<sid>\d+)/(?P<tid>\d+)/$',
                v(self.schedule_view_track),
                name='conference-conference-schedule-track'),

            url(r'^(?P<cid>[\w-]+)/stats/$',
                v(self.stats_list),
                name='conference-ticket-stats'),
            url(r'^(?P<cid>[\w-]+)/stats/details$',
                v(self.stats_details),
                name='conference-ticket-stats-details'),
            url(r'^(?P<cid>[\w-]+)/stats/details.csv$',
                v(self.stats_details_csv),
                name='conference-ticket-stats-details-csv'),
        )
        return urls + super(ConferenceAdmin, self).get_urls()

    def schedule_view_talks(self, conf):
        tids = []
        if conf.code == settings.CONFERENCE:
            results = utils.voting_results()
            if results is not None:
                tids = map(lambda x: x[0], results)
        complete = models.Talk.objects\
            .filter(conference=conf.code, status='accepted')\
            .order_by('title')\
            .values_list('id', flat=True)

        haystack = set(tids)
        missing = []
        for c in complete:
            if c not in haystack:
                missing.append(c)
        return dataaccess.talks_data(missing + tids)

    def schedule_view(self, request, cid):
        conf = models.Conference.objects.get(code=cid)
        schedules = dataaccess.schedules_data(models.Schedule.objects\
            .filter(conference=conf)\
            .values_list('id', flat=True)
        )
        tracks = []
        for sch in schedules:
            tks = sorted(sch['tracks'].values(), key=lambda x: x.order)
            tracks.append([ sch['id'], [ t for t in tks ] ])

        from conference.forms import EventForm
        return render_to_response(
            'admin/conference/conference/schedule_view.html',
            {
                'conference': conf,
                'tracks': tracks,
                'talks': self.schedule_view_talks(conf),
                'event_form': EventForm(),
            },
            context_instance=template.RequestContext(request)
        )

    def schedule_view_track(self, request, cid, sid, tid):
        get_object_or_404(models.Track, schedule__conference=cid, schedule=sid, id=tid)
        from datetime import time
        tt = utils.TimeTable2\
            .fromTracks([tid])\
            .adjustTimes(time(8, 00), time(18, 30))
        return render_to_response(
            'admin/conference/conference/schedule_view_schedule.html',
            { 'timetable': tt, },
            context_instance=template.RequestContext(request))

    def _stat_wrapper(self, func, conf):
        def wrapper(*args, **kwargs):
            result = func(conf, *args, **kwargs)
            if 'columns' not in result:
                result = {
                    'columns': (
                        ('total', 'Total'),
                    ),
                    'data': result,
                }
            result['id'] = wrapper.stat_id
            return result
        wrapper.stat_id = func.__name__
        return wrapper

    def available_stats(self, conf):
        stats = []
        for path in settings.ADMIN_ATTENDEE_STATS:
            func = utils.dotted_import(path)
            w = {
                'get_data': self._stat_wrapper(func, conf),
                'short_description': getattr(func, 'short_description', func.__name__.replace('_', ' ').strip()),
                'description': getattr(func, 'description', func.__doc__),
            }
            stats.append(w)
        return stats

    def single_stat(self, conf, sid, code):
        for s in self.available_stats(conf):
            if s['get_data'].stat_id == sid:
                r = s['get_data']
                s['get_data'] = lambda: r(code=code)
                return s

    def stats_list(self, request, cid):
        stats = []
        stats = self.available_stats(cid)

        return render_to_response(
            'admin/conference/conference/attendee_stats.html',
            {
                'conference': cid,
                'stats': stats,
            },
            context_instance=template.RequestContext(request))

    def stats_details(self, request, cid):
        sid, rowid = request.GET['code'].split('.')
        stat = self.single_stat(cid, sid, rowid)

        from conference.forms import AdminSendMailForm
        preview = None
        if request.method == 'POST':
            form = AdminSendMailForm(data=request.POST, real_usage='preview' not in request.POST)
            if form.is_valid():
                uids = [ x['uid'] for x in stat['get_data']()['data']]
                try:
                    pid = int(request.POST['preview_id'])
                except:
                    pid = None
                if pid is None or pid not in uids:
                    pid = None
                if 'preview' in request.POST:
                    preview = form.preview(pid or uids[0])[0]
                else:
                    if form.cleaned_data['send_email']:
                        from django.contrib import messages
                        c = form.send_emails(uids, request.user.email)
                        messages.add_message(request, messages.INFO, '{0} emails sent'.format(c))
                        form.save_email()
                        form = AdminSendMailForm()
        else:
            form = AdminSendMailForm()
        return render_to_response(
            'admin/conference/conference/attendee_stats_details.html',
            {
                'conference': cid,
                'stat': stat,
                'stat_code': '%s.%s' % (sid, rowid),
                'form': form,
                'preview': preview,
                'email_log': settings.ADMIN_TICKETS_STATS_EMAIL_LOG,
            },
            context_instance=template.RequestContext(request))

    def stats_details_csv(self, request, cid):
        sid, rowid = request.GET['code'].split('.')
        stat = self.single_stat(cid, sid, rowid)

        buff = StringIO()
        result = stat['get_data']()

        colid = []
        colnames = []
        for cid, cname in result['columns']:
            colid.append(cid)
            colnames.append(cname)

        writer = csv.writer(buff)
        writer.writerow(colnames)
        for row in result['data']:
            writer.writerow([ row.get(c, '').encode('utf-8') for c in colid ])

        fname = '[%s] %s.csv' % (settings.CONFERENCE, stat['short_description'])
        r = http.HttpResponse(buff.getvalue(), content_type="text/csv")
        r['content-disposition'] = 'attachment; filename="%s"' % fname
        return r

admin.site.register(models.Conference, ConferenceAdmin)

class DeadlineAdmin(admin.ModelAdmin):
    list_display = ('date', '_headline', '_text', '_expired')
    date_hierarchy = 'date'

    def _headline(self, obj):
        contents = dict((c.language, c) for c in obj.deadlinecontent_set.all())
        for l, lname in dsettings.LANGUAGES:
            try:
                content = contents[l]
            except KeyError:
                continue
            if content.headline:
                return content.headline
        else:
            return '[No Headline]'
    _headline.short_description = 'headline'
    _headline.allow_tags = True

    def _text(self, obj):
        contents = dict((c.language, c) for c in obj.deadlinecontent_set.all())
        for l, lname in dsettings.LANGUAGES:
            try:
                content = contents[l]
            except KeyError:
                continue
            if content.body:
                return content.body
        else:
            return '[No Body]'
    _text.short_description = 'testo'
    _text.allow_tags = True

    def _expired(self, obj):
        return not obj.isExpired()
    _expired.boolean = True

    # Nella pagina per la creazione/modifica di una deadline voglio mostrare
    # una textarea per ogni lingua abilitata nei settings. Per fare questo
    # ridefinisco due metodi di ModelAdmin:
    #     * get_form
    #     * save_model
    # Con il primo aggiungo all'oggetto ModelForm ritornato dalla classe base
    # un CharField per ogni lingua configurata; la form ritornata da questo
    # metodo viene renderizzata nella pagina HTML.
    # Con il secondo oltre a salvare l'istanza di Deadline creo/modifico le
    # istanze di DeadlineContent in funzione delle lingue.

    def get_fieldsets(self, request, obj=None):
        fieldsets = super(DeadlineAdmin, self).get_fieldsets(request, obj=obj)

        fields = fieldsets[0][1]['fields']

        for lang_code, _ in dsettings.LANGUAGES:
            fields.append('headline_' + lang_code)
            fields.append('body_' + lang_code)
        return fieldsets

    def get_form(self, request, obj=None, **kwargs):
        initials = {}
        if obj:
            initials = dict((c.language, (c.headline, c.body)) for c in obj.deadlinecontent_set.all())

        class DeadlineForm(forms.ModelForm):
            class Meta:
                model = models.Deadline
                fields = ('date',)
            def __init__(self, *args, **kw):
                super(DeadlineForm, self).__init__(*args, **kw)
                for lang_code, _ in dsettings.LANGUAGES:
                    headline = forms.CharField(max_length=200, required=False)
                    try:
                        headline.initial = initials[lang_code][0]
                    except:
                        pass
                    self.fields['headline_' + lang_code] = headline

                    body = forms.CharField(widget=forms.Textarea, required=False)
                    try:
                        body.initial = initials[lang_code][1]
                    except:
                        pass
                    self.fields['body_' + lang_code] = body
        return DeadlineForm

    def save_model(self, request, obj, form, change):
        obj.save()
        data = form.cleaned_data
        for l, _ in dsettings.LANGUAGES:
            if change:
                try:
                    instance = models.DeadlineContent.objects.get(deadline=obj, language=l)
                except models.DeadlineContent.DoesNotExist:
                    instance = models.DeadlineContent()
            else:
                instance = models.DeadlineContent()
            if not instance.id:
                instance.deadline = obj
                instance.language = l
            instance.headline = data.get('headline_' + l, '')
            instance.body = data.get('body_' + l, '')
            instance.save()

admin.site.register(models.Deadline, DeadlineAdmin)

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import ReverseGenericRelatedObjectsDescriptor

class MultiLingualFormMetaClass(forms.models.ModelFormMetaclass):
    def __new__(mcs, name, bases, attrs):
        new_class = super(MultiLingualFormMetaClass, mcs).__new__(mcs, name, bases, attrs)

        multilingual_fields = new_class.multilingual_fields = []
        model = new_class._meta.model
        if not model:
            return new_class

        for name, f in model.__dict__.items():
            if isinstance(f, ReverseGenericRelatedObjectsDescriptor):
                if f.field.related.model is models.MultilingualContent:
                    multilingual_fields.append(name)

        widget = attrs.get('multilingual_widget', forms.Textarea)
        form_fields = {}
        for field_name in multilingual_fields:
            for lang, _ in dsettings.LANGUAGES:
                text = forms.CharField(widget=widget, required=False)
                full_name = u'{name}_{lang}'.format(name=field_name, lang=lang)
                form_fields[full_name] = text

        new_class.declared_fields.update(form_fields)
        new_class.base_fields.update(form_fields)
        return new_class

class MultiLingualForm(forms.ModelForm):
    __metaclass__ = MultiLingualFormMetaClass

    def __init__(self, *args, **kw):
        super(MultiLingualForm, self).__init__(*args, **kw)

        if self.instance:
            self._init_multilingual_fields()

    def _init_multilingual_fields(self):
        for field_name in self.multilingual_fields:
            translations = getattr(self.instance, field_name).filter(content=field_name)
            for t in translations:
                form_field = '{name}_{lang}'.format(name=field_name, lang=t.language)
                try:
                    self.fields[form_field].initial = t.body
                except KeyError:
                    # Someone probably removed a previously configured
                    # language; nothing must we can do other than to
                    # ignore the error
                    pass

    def _save_translations(self, o):
        for field_name in self.multilingual_fields:
            for l, _ in dsettings.LANGUAGES:
                form_field = '{name}_{lang}'.format(name=field_name, lang=l)
                text = self.cleaned_data[form_field]
                try:
                    translation = getattr(o, field_name).get(content=field_name, language=l)
                except models.MultilingualContent.DoesNotExist:
                    translation = models.MultilingualContent(
                        content_object=o,
                        language=l,
                        content=field_name)
                translation.body = text
                translation.save()

    def save(self, commit=True):
        o = super(MultiLingualForm, self).save(commit=commit)
        if not commit:
            base_m2m = self.save_m2m
            def save_m2m():
                base_m2m()
                self._save_translations(o)
            self.save_m2m = save_m2m
        else:
            self._save_translations(o)
        return o

    @classmethod
    def for_model(cls, model_class):
        class Form(cls):
            class Meta:
                model = model_class
                fields = '__all__'
        return Form

class TalkSpeakerInlineAdminForm(forms.ModelForm):
    class Meta:
        model = models.TalkSpeaker
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(TalkSpeakerInlineAdminForm, self).__init__(*args, **kwargs)
        data = models.Speaker.objects\
            .values('user', 'user__first_name', 'user__last_name')\
            .order_by('user__first_name', 'user__last_name')
        self.fields['speaker'] = forms.TypedChoiceField(choices=[('', '---------')] + [
            (x['user'], '%s %s' % (x['user__first_name'], x['user__last_name']))
            for x in data
        ], coerce=int)

    def clean_speaker(self):
        data = self.cleaned_data
        return models.Speaker.objects.get(user=data['speaker'])

class TalkSpeakerInlineAdmin(admin.TabularInline):
    model = models.TalkSpeaker
    form = TalkSpeakerInlineAdminForm
    extra = 1

class SpeakerAdminForm(forms.ModelForm):
    class Meta:
        model = models.Speaker
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(SpeakerAdminForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = self.fields['user'].queryset.order_by('username')

class SpeakerAdmin(admin.ModelAdmin):
    list_display = ('_avatar', '_user', '_email', '_company')
    search_fields = ('user__first_name', 'user__last_name', 'user__email',
                     'user__attendeeprofile__company')
    list_filter = ('talk__conference', 'talk__status', 
                   'user__attendeeprofile__company')
    list_select_related = True
    form = SpeakerAdminForm
    inlines = (TalkSpeakerInlineAdmin,)

    def get_queryset(self, request):
        qs = super(SpeakerAdmin, self).get_queryset(request)
        qs = qs.select_related('user__attendeeprofile')
        if request.GET:
            # Make sure we do an AND query, not an or one as implicit by
            # the Django admin .list_filter
            conf = request.GET.get('talk__conference', None)
            status = request.GET.get('talk__status__exact', None)
            if conf is not None and status is not None:
                qs = qs.filter(talk__conference=conf,
                               talk__status__exact=status)
        return qs

    def get_urls(self):
        urls = super(SpeakerAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^stats/list/$', self.admin_site.admin_view(self.stats_list), name='conference-speaker-stat-list'),
        )
        return my_urls + urls

    def stats_list(self, request):
        qs = models.TalkSpeaker.objects\
            .filter(talk__conference=settings.CONFERENCE)\
            .order_by('speaker__user__first_name', 'speaker__user__last_name')\
            .distinct()\
            .values_list('speaker', flat=True)
        # preload the profiles because we need to help the template
        dataaccess.profiles_data(qs)
        speakers = dataaccess.speakers_data(qs)
        groups = {}
        for t, _ in models.TALK_TYPE:
            sids = set(qs.filter(talk__type=t))
            data = [ x for x in speakers if x['user'] in sids ]
            if data:
                groups[t] = data
        return render_to_response(
            'admin/conference/speaker/stats_list.html',
            {
                'speakers': speakers,
                'groups': groups,
            },
            context_instance=template.RequestContext(request)
        )

    def _user(self, o):
        if o.user.attendeeprofile:
            p = urlresolvers.reverse('conference-profile', kwargs={'slug': o.user.attendeeprofile.slug})
        else:
            p = 'javascript:alert("profile not set")'
        return '<a href="%s">%s %s</a>' % (p, o.user.first_name, o.user.last_name)
    _user.allow_tags = True
    _user.admin_order_field = 'user__first_name'

    def _company(self, o):
        if o.user.attendeeprofile:
            return o.user.attendeeprofile.company
    _company.admin_order_field = 'user__attendeeprofile__company'
    
    def _email(self, o):
        return o.user.email
    _user.admin_order_field = 'user__email'

    def _avatar(self, o):
        try:
            img = o.user.attendeeprofile.image
        except models.AttendeeProfile.DoesNotExist:
            img = None
        if not img:
            return '<div style="height: 32px; width: 32px"> </div>'
        return '<img src="%s" height="32" />' % (img.url,)
    _avatar.allow_tags = True

admin.site.register(models.Speaker, SpeakerAdmin)

class TalkAdminForm(MultiLingualForm):
    class Meta:
        model = models.Talk
        fields = '__all__'

    # Try to check if the url will match the pattern of Viddler
    video_check = re.compile(r'http://www\.viddler\.com/player/[^/]+/?')

    def clean_video(self):
        match = self.video_check.search(self.cleaned_data['video'])
        if match:
            self.cleaned_data['video'] = match.group(0)
        else:
            self.cleaned_data['video'] = ''
        return self.cleaned_data['video']

class TalkAdmin(admin.ModelAdmin):
    actions = ('do_accept_talks_in_schedule', 'do_speakers_data',)
    list_display = ('title', 'conference', '_speakers', 'duration', 'status', '_slides', '_video')
    list_editable = ('status',)
    list_filter = ('conference', 'status',)
    ordering = ('-conference', 'title')
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ('title',)
    inlines = (TalkSpeakerInlineAdmin,)

    form = TalkAdminForm

    def get_paginator(self, request, queryset, per_page, orphans=0, allow_empty_first_page=True):
        # Use dataaccess to do only one query to the database, and try to fetch
        # all the information of the speaker and the talks.
        talks = dataaccess.talks_data(queryset.values_list('id', flat=True))
        self.cached_talks = dict([(x['id'], x) for x in talks])
        sids = [ s['id'] for t in talks for s in t['speakers'] ]
        profiles = dataaccess.profiles_data(sids)
        self.cached_profiles = dict([(x['id'], x) for x in profiles])
        return super(TalkAdmin, self).get_paginator(request, queryset, per_page, orphans, allow_empty_first_page)

    def changelist_view(self, request, extra_context=None):
        if not request.GET.has_key('conference') and not request.GET.has_key('conference__exact'):
            q = request.GET.copy()
            q['conference'] = settings.CONFERENCE
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(TalkAdmin,self).changelist_view(request, extra_context=extra_context)

    def _speakers(self, obj):
        data = self.cached_talks.get(obj.id)
        output = []
        for x in data['speakers']:
            args = {
                'url': urlresolvers.reverse('admin:conference_speaker_change', args=(x['id'],)),
                'name': x['name'],
                'mail': self.cached_profiles[x['id']]['email'],
            }
            output.append('<a href="%(url)s">%(name)s</a> (<a href="mailto:%(mail)s">mail</a>)' % args)
        return '<br />'.join(output)
    _speakers.allow_tags = True

    def _slides(self, obj):
        return bool(obj.slides)
    _slides.boolean = True
    _slides.admin_order_field = 'slides'

    def _video(self, obj):
        return bool(obj.video_type) and (bool(obj.video_url) or bool(obj.video_file))
    _video.boolean = True
    _video.admin_order_field = 'video_type'

    #@transaction.atomic
    def do_accept_talks_in_schedule(self, request, queryset):
        conf = set(t.conference for t in queryset)
        next = urlresolvers.reverse('admin:conference_talk_changelist')
        if len(conf) > 1:
            self.message_user(request, 'Selected talks spans multiple conferences')
            return redirect(next)
        conference_talks = set(x['id'] for x in models.Talk.objects\
                                                    .filter(id__in=models.Event.objects\
                                                            .filter(schedule__conference=conf.pop())\
                                                            .exclude(talk=None)\
                                                            .values('talk'))\
                                                    .values('id'))
        for t in queryset:
            if t.id in conference_talks:
                t.status = 'accepted'
            else:
                t.status = 'proposed'
            t.save()
        return redirect(next)
    do_accept_talks_in_schedule.short_description = 'Accept talks that takes place in conference schedule'

    def do_speakers_data(self, request, queryset):
        buff = StringIO()
        writer = csv.writer(buff)
        for t in queryset:
            for s in t.get_all_speakers():
                name = '{} {}'.format(s.user.first_name, s.user.last_name)
                writer.writerow((t.status, t.title.encode('utf-8'), name.encode('utf-8'), s.user.email.encode('utf-8')))
        response = http.HttpResponse(buff.getvalue(), content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename=speakers.csv'
        return response
    do_speakers_data.short_description = 'Speakers data'

admin.site.register(models.Talk, TalkAdmin)

class SponsorIncomeInlineAdmin(admin.TabularInline):
    model = models.SponsorIncome
    extra = 1

class SponsorAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("sponsor",)}
    list_display = ('sponsor', 'url', 'conferences')
    inlines = [ SponsorIncomeInlineAdmin ]

    def conferences(self, obj):
        """List the sponsorised talks by the sponsor"""
        return ', '.join(s.conference for s in obj.sponsorincome_set.all())

admin.site.register(models.Sponsor, SponsorAdmin)

class MediaPartnerConferenceInlineAdmin(admin.TabularInline):
    model = models.MediaPartnerConference
    extra = 1

class MediaPartnerAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("partner",)}
    list_display = ('partner', 'url', 'conferences')
    inlines = [ MediaPartnerConferenceInlineAdmin ]

    def conferences(self, obj):
        """Will give the conferences which the partner has participated"""
        return ', '.join(s.conference for s in obj.mediapartnerconference_set.all())

admin.site.register(models.MediaPartner, MediaPartnerAdmin)

class TrackInlineAdmin(admin.TabularInline):
    model = models.Track
    extra = 1

class EventInlineAdmin(admin.TabularInline):
    model = models.Event
    extra = 3

from django.template import Template

class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('conference', 'slug', 'date')
    inlines = [
        TrackInlineAdmin,
        EventInlineAdmin
    ]

    def get_urls(self):
        urls = super(ScheduleAdmin, self).get_urls()
        v = self.admin_site.admin_view
        my_urls = patterns('',
            url(r'^stats/$',
                v(self.expected_attendance),
                name='conference-schedule-expected_attendance'),
            url(r'^(?P<sid>\d+)/events/$',
                v(self.events),
                name='conference-schedule-events'),
            url(r'^(?P<sid>\d+)/events/(?P<eid>\d+)$',
                v(self.event),
                name='conference-schedule-event'),
            url(r'^(?P<sid>\d+)/tracks/(?P<tid>[\d]+)$',
                v(self.tracks),
                name='conference-schedule-tracks'),
        )
        return my_urls + urls

    @common.decorators.render_to_json
    #@transaction.atomic
    def events(self, request, sid):
        sch = get_object_or_404(models.Schedule, id=sid)
        if request.method != 'POST':
            return http.HttpResponseNotAllowed(('POST',))
        from conference.forms import EventForm
        form = EventForm(data=request.POST)
        output = {}
        if form.is_valid():
            event = form.save(commit=False)
            event.schedule = sch
            event.save()
            for t in form.cleaned_data['event_tracks']:
                models.EventTrack(event=event, track=t).save()
            output = {
                'event': event.id,
            }
        return output

    #@transaction.atomic
    def event(self, request, sid, eid):
        ev = get_object_or_404(models.Event, schedule=sid, id=eid)

        class SimplifiedTalkForm(forms.Form):
            tags = forms.CharField(
                max_length=200, required=False,
                help_text='comma separated list of tags. Something like: special, break, keynote'
            )
            bookable = forms.BooleanField(
                required=False,
                help_text='check if the event expect a reservation'
            )
            seats = forms.IntegerField(
                min_value=0,
                required=False,
                help_text='Seats available. Override the track default if set'
            )
            sponsor = forms.ModelChoiceField(
                queryset=models.Sponsor.objects\
                    .filter(sponsorincome__conference=settings.CONFERENCE)\
                    .order_by('sponsor'),
                required=False
            )
            tracks = forms.ModelMultipleChoiceField(
                queryset=models.Track.objects\
                    .filter(schedule=ev.schedule)
            )

        class SimplifiedCustomForm(forms.Form):
            custom = forms.CharField(max_length=200)
            abstract = forms.CharField(widget=forms.Textarea, required=False)
            duration = forms.IntegerField(min_value=0)
            tags = forms.CharField(
                max_length=200, required=False,
                help_text='comma separated list of tags. Something like: special, break, keynote'
            )
            bookable = forms.BooleanField(
                required=False,
                help_text='check if the event expect a reservation'
            )
            seats = forms.IntegerField(
                min_value=0,
                required=False,
                help_text='Seats available. Override the track default if set'
            )
            sponsor = forms.ModelChoiceField(
                queryset=models.Sponsor.objects\
                    .filter(sponsorincome__conference=settings.CONFERENCE)\
                    .order_by('sponsor'),
                required=False
            )
            tracks = forms.ModelMultipleChoiceField(
                queryset=models.Track.objects\
                    .filter(schedule=ev.schedule)
            )

        class MoveEventForm(forms.Form):
            start_time = forms.TimeField()
            track = forms.ModelChoiceField(queryset=models.Track.objects.all(), required=False)

        class SplitEventForm(forms.Form):
            split_time = forms.IntegerField(min_value=1)

        if request.method == 'POST':
            if 'delete' in request.POST:
                ev.delete()
            elif 'save' in request.POST or 'copy' in request.POST or 'update' in request.POST:
                if ev.talk_id:
                    form = SimplifiedTalkForm(data=request.POST)
                else:
                    form = SimplifiedCustomForm(data=request.POST)
                if form.is_valid():
                    data = form.cleaned_data
                    ev.sponsor = data['sponsor']
                    ev.tags = data['tags']
                    ev.bookable = data['bookable']
                    ev.seats = data['seats'] or 0
                    if not ev.talk_id:
                        ev.custom = data['custom']
                        ev.abstract = data['abstract']
                        ev.duration = data['duration']
                    ev.save()
                    models.EventTrack.objects.filter(event=ev).delete()
                    for t in data['tracks']:
                        models.EventTrack(event=ev, track=t).save()
                    if 'copy' in request.POST:
                        schedules = models.Schedule.objects\
                            .filter(conference=ev.schedule.conference)\
                            .exclude(id=ev.schedule_id)
                        tracks = models.Track.objects\
                            .filter(schedule__in=schedules)\
                            .values('id', 'track', 'schedule')
                        tmap = defaultdict(dict)
                        for t in tracks:
                            tmap[t['schedule']][t['track']] = t['id']
                        etracks = set(models.EventTrack.objects\
                            .filter(event=ev)\
                            .values_list('track__track', flat=True))
                        for sid, tracks in tmap.items():
                            if models.Event.objects.filter(schedule=sid, start_time=ev.start_time).exists():
                                continue
                            ev.id = None
                            ev.schedule_id = sid
                            ev.save()
                            for x in etracks:
                                if x in tracks:
                                    models.EventTrack(event=ev, track_id=tracks[x]).save()
                    elif 'update' in request.POST and not ev.talk_id:
                        eids = models.EventTrack.objects\
                            .filter(track__in=data['tracks'], event__custom=ev.custom)\
                            .exclude(event=ev)\
                            .values('event')
                        events = models.Event.objects\
                            .filter(id__in=eids)
                        for e in events:
                            e.sponsor = ev.sponsor
                            e.tags = ev.tags
                            e.bookable = ev.bookable
                            e.seats = ev.seats
                            e.abstract = ev.abstract
                            e.duration = ev.duration
                            e.save()
            elif 'move' in request.POST:
                form = MoveEventForm(data=request.POST)
                if form.is_valid():
                    data = form.cleaned_data
                    ev.start_time = data['start_time']
                    ev.save()
                    if data.get('track'):
                        models.EventTrack.objects.filter(event=ev).delete()
                        models.EventTrack(event=ev, track=data['track']).save()
            elif 'split' in request.POST:
                form = SplitEventForm(data=request.POST)
                if form.is_valid():
                    data = form.cleaned_data
                    ev.split(time=data['split_time'])
            else:
                raise ValueError()
            return http.HttpResponse(content=json_dumps({}), content_type="text/javascript")
        else:
            if ev.talk_id != None:
                form = SimplifiedTalkForm(data={
                    'sponsor': ev.sponsor.id if ev.sponsor else None,
                    'tags': ev.tags,
                    'bookable': ev.bookable,
                    'seats': ev.seats,
                    'tracks': list(ev.tracks.all().values_list('id', flat=True)),
                })
            else:
                form = SimplifiedCustomForm(data={
                    'sponsor': ev.sponsor.id if ev.sponsor else None,
                    'tags': ev.tags,
                    'bookable': ev.bookable,
                    'seats': ev.seats,
                    'custom': ev.custom,
                    'abstract': ev.abstract,
                    'duration': ev.duration,
                    'tracks': list(ev.tracks.all().values_list('id', flat=True)),
                })
            tpl = Template('''
            <form class="async" method="POST" action="{% url "admin:conference-schedule-event" sid eid %}">{% csrf_token %}
                <table>{{ form }}</table>
                <div class="submit-row">
                    <input type="submit" name="save" value="save"/>
                    <input type="submit" name="delete" value="delete"/>
                    <input type="submit" name="copy" title="repeat in all schedules/days" value="save and repeat"/>
                    <input type="submit" name="update" title="updates events with the same title in the tracks with the same name" value="save and update"/>
                </div>
            </form>
            ''')
            ctx = {
                'form': form,
                'sid': sid,
                'eid': eid,
            }
            return http.HttpResponse(tpl.render(template.RequestContext(request, ctx)))

    #@transaction.atomic
    def tracks(self, request, sid, tid):
        track = get_object_or_404(models.Track, schedule=sid, id=tid)
        from conference.forms import TrackForm
        if request.method == 'POST':
            tracks = models.Track.objects\
                .filter(schedule__conference=track.schedule.conference, track=track.track)
            for t in tracks:
                form = TrackForm(instance=t, data=request.POST)
                form.save()
            output = {
                'tracks': [ t.id for t in tracks ],
            }
            return http.HttpResponse(content=json_dumps(output), content_type="text/javascript")
        else:
            form = TrackForm(instance=track)
            tpl = Template('''
            <form class="async" method="POST" action="{% url "admin:conference-schedule-tracks" sid tid %}">{% csrf_token %}
                <table>{{ form }}</table>
                <div class="submit-row">
                    <input type="submit" />
                </div>
            </form>
            ''')
            ctx = {
                'form': form,
                'sid': sid,
                'tid': tid,
            }
            return http.HttpResponse(tpl.render(template.RequestContext(request, ctx)))

    def expected_attendance(self, request):
        allevents = defaultdict(dict)
        for e, info in models.Schedule.objects.expected_attendance(settings.CONFERENCE).items():
            allevents[e.schedule][e] = info
        data = {}
        for s, events in allevents.items():
            data[s] = entry = {
                'morning': [],
                'afternoon': [],
            }
            for e, info in events.items():
                item = dict(info)
                item['event'] = e
                if e.start_time.hour < 13 and e.start_time.minute < 30:
                    entry['morning'].append(item)
                else:
                    entry['afternoon'].append(item)
        ctx = {
            'schedules': sorted(data.items(), key=lambda x: x[0].date),
        }
        return render_to_response('conference/admin/schedule_expected_attendance.html', ctx, context_instance=template.RequestContext(request))

admin.site.register(models.Schedule, ScheduleAdmin)

class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', '_contacts', 'address', 'affiliated', 'visible')
    list_filter = ('visible', 'affiliated' )
    search_fields = [ 'name', 'address' ]

    def _contacts(self, obj):
        h = ""
        if obj.email:
            h += '<a href="mailto:%s">%s</a> ' % (obj.email, obj.email)
        if obj.telephone:
            h+= obj.telephone
        return h
    _contacts.allow_tags = True
    _contacts.short_description = 'Contatti'

admin.site.register(models.Hotel, HotelAdmin)

class DidYouKnowAdmin(admin.ModelAdmin):
    list_display = ('_message', 'visible')

    form = MultiLingualForm.for_model(models.DidYouKnow)

    def _message(self, o):
        messages = dict( (c.language, c) for c in o.messages.all() if c.body)

        try:
            return messages[dsettings.LANGUAGES[0][0]].body
        except KeyError:
            if messages:
                return messages.values()[0].body
            else:
                return 'no messages'

admin.site.register(models.DidYouKnow, DidYouKnowAdmin)

class QuoteAdmin(admin.ModelAdmin):
    list_display = ('who', 'conference', '_text')

    def _text(self, o):
        return o.text[:80]

admin.site.register(models.Quote, QuoteAdmin)

class SpecialPlaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'email')

admin.site.register(models.SpecialPlace, SpecialPlaceAdmin)


class FilterFareByTicketCode(admin.SimpleListFilter):

    def lookups(self, request, model_admin):
        return self.filter_by

    def queryset(self, request, queryset):
        if self.value() in dict(self.filter_by):
            regex = FARE_CODE_REGEXES[self.parameter_name][self.value()]
            return queryset.filter(code__regex=regex)


class FilterFareByType(FilterFareByTicketCode):

    title = 'Fare Type'
    parameter_name = 'types'    # this is significant name
    filter_by = FARE_CODE_TYPES._doubles


class FilterFareByVariant(FilterFareByTicketCode):

    title = 'Fare Variant'
    parameter_name = 'variants'  # this is significant name
    filter_by = FARE_CODE_VARIANTS._doubles


class FilterFareByGroup(FilterFareByTicketCode):

    title = 'Fare Group'
    parameter_name = 'groups'
    filter_by = FARE_CODE_GROUPS._doubles


class FareAdmin(admin.ModelAdmin):
    list_display = ('conference', 'code', 'name', 'price', 'recipient_type',
                    'start_validity', 'end_validity')
    list_filter = ('conference',
                   'ticket_type',
                   FilterFareByType,
                   FilterFareByVariant,
                   FilterFareByGroup)
    list_editable = ('price', 'start_validity', 'end_validity')
    list_display_links = ('code', 'name')
    ordering = ('conference', 'start_validity', 'code')

    def changelist_view(self, request, extra_context=None):
        if not request.GET.has_key('conference') and not request.GET.has_key('conference__exact'):
            q = request.GET.copy()
            q['conference'] = settings.CONFERENCE
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(FareAdmin,self).changelist_view(request, extra_context=extra_context)

admin.site.register(models.Fare, FareAdmin)

class TicketAdmin(admin.ModelAdmin):
    list_display = ('_name', '_buyer', '_conference', '_ticket', 'ticket_type',)
    search_fields = ('name', 'user__first_name', 'user__last_name', 'user__email')
    list_filter = ('fare__conference', 'fare__ticket_type', 'ticket_type',)

    if settings.TICKET_BADGE_ENABLED:
        actions = ('do_ticket_badge',)

    class Media:
        js = (
            'conference/jquery-ui/js/jquery-1.7.1.min.js',
            'conference/jquery-flot/jquery.flot.js',
        )

    def _name(self, o):
        if o.name.strip():
            return o.name
        else:
            return '(no attendee name set)'
    _name.admin_order_field = 'name'

    def _buyer(self, o):
        return '%s %s' % (o.user.first_name, o.user.last_name)
    _buyer.admin_order_field = 'user__first_name'

    def _conference(self, o):
        return o.fare.conference
    _conference.admin_order_field = 'fare__conference'

    def _ticket(self, o):
        return o.fare.code
    _ticket.admin_order_field = 'fare__code'

    def changelist_view(self, request, extra_context=None):
        if not request.GET:
            q = request.GET.copy()
            q['fare__conference'] = settings.CONFERENCE
            q['fare__ticket_type__exact'] = 'conference'
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(TicketAdmin,self).changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super(TicketAdmin, self).get_queryset(request)
        qs = qs.select_related('user', 'fare',)
        return qs

    def do_ticket_badge(self, request, qs):
        output = utils.render_badge(qs, cmdargs=settings.TICKET_BADGE_PROG_ARGS_ADMIN)
        name, output_dir, _ = output[0]
        tar = utils.archive_dir(output_dir)
        response = http.HttpResponse(tar, content_type="application/x-gzip")
        response['Content-Disposition'] = 'attachment; filename=badge-%s.tar.gz' % name
        return response
    do_ticket_badge.short_description = 'Ticket Badge'

    def get_urls(self):
        urls = super(TicketAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^stats/data/$', self.admin_site.admin_view(self.stats_data_view), name='conference-ticket-stats-data'),
        )
        return my_urls + urls

    def stats_data(self):
        from django.db.models import Q
        from collections import defaultdict
        import datetime

        conferences = models.Conference.objects\
            .order_by('conference_start')

        output = {}
        for c in conferences:
            tickets = models.Ticket.objects\
                .filter(fare__conference=c, frozen=False)\
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
            deadlines = models.DeadlineContent.objects\
                .filter(language=dsettings.LANGUAGES[0][0])\
                .filter(deadline__date__lte=c.conference_start, deadline__date__gte=dlimit)\
                .select_related('deadline')\
                .order_by('deadline__date')
            markers = [
                ((d.deadline.date - c.conference_start).days, 'CAL: ' + (d.headline or d.body))
                for d in deadlines
            ]

            output[c.code] = {
                'data': data,
                'markers': markers,
            }
        return output

    def stats_data_view(self, request):
        output = self.stats_data()
        return http.HttpResponse(json_dumps(output), 'text/javascript')

admin.site.register(models.Ticket, TicketAdmin)

class ConferenceTagAdmin(admin.ModelAdmin):
    actions = ('do_merge_tags',)
    list_display = ('slug', 'name', 'category', '_usage',)
    list_editable = ('name', 'category')
    list_filter = ('category',)
    list_per_page = 500
    prepopulated_fields = {"slug": ("name",)}
    ordering = ('name',)

    def get_urls(self):
        urls = super(ConferenceTagAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^merge/$', self.admin_site.admin_view(self.merge_tags), name='conference-conferencetag-merge'),
        )
        return my_urls + urls

    def get_queryset(self, request):
        from django.db.models import Count
        qs = super(ConferenceTagAdmin, self).get_queryset(request)
        qs = qs.annotate(usage=Count('conference_conferencetaggeditem_items'))
        return qs

    def _usage(self, o):
        return o.usage
    _usage.admin_order_field = 'usage'

    def do_merge_tags(self, request, queryset):
        ids = queryset.order_by().values_list('id', flat=True)
        if not ids:
            self.message_user(request, "No tag selected")
            return
        q = http.QueryDict('', mutable=True)
        q.setlist('tags', ids)
        url = urlresolvers.reverse('admin:conference-conferencetag-merge') + '?' + q.urlencode()
        return http.HttpResponseRedirect(url)
    do_merge_tags.short_description = "Merge the selected tags"

    def merge_tags(self, request):
        if request.method == 'POST':
            tags_id = request.session.get('conference_tag_merge_ids', [])
        else:
            tags_id = map(int, request.GET.getlist('tags'))
        if not tags_id:
            return http.HttpResponseBadRequest('no tags specified')
        if request.method == 'POST':
            target = int(request.POST.get('target', -1))
            if target not in tags_id:
                return http.HttpResponseBadRequest('invalid target tag')
            tags = models.ConferenceTag.objects\
                .filter(id__in=tags_id)
            discard = [ t for t in tags if t.id != target ]

            # We don't want to use the bulk operation for the update of
            # ConferenceTaggedItem and the cancellation of ConferenceTag
            # (objects.update, objects.delete) because the management of the
            # cache of dataaccess is based on the signals for the coherence.
            for item in models.ConferenceTaggedItem.objects.filter(tag__in=discard):
                item.tag_id=target
                item.save()

            for t in discard:
                t.delete()
            self.message_user(request, "tag merged")
            return http.HttpResponseRedirect(urlresolvers.reverse('admin:conference_conferencetag_changelist'))
        else:
            request.session['conference_tag_merge_ids'] = tags_id
        tags = models.ConferenceTag.objects\
            .filter(id__in=tags_id)\
            .order_by_usage()
        ctx = {
            'tags': tags,
        }
        return render_to_response('admin/conference/conferencetag/merge.html', ctx, context_instance=template.RequestContext(request))


admin.site.register(models.ConferenceTag, ConferenceTagAdmin)


class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('datestamp', 'currency', 'rate')


admin.site.register(models.ExchangeRate, ExchangeRateAdmin)


class CaptchaQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'enabled')
    list_filter = ('enabled',)


admin.site.register(models.CaptchaQuestion)
