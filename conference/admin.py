import csv
import logging
from collections import defaultdict
from io import StringIO

from django import forms
from django import http
from django.contrib import admin
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.contenttypes.fields import (
    ReverseGenericManyToOneDescriptor,
)
from django.urls import reverse, re_path
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe

import common.decorators
from common.jsonify import json_dumps
from conference import dataaccess, models, utils
from conference.forms import TrackForm, EventForm
from assopy.models import Vat, VatFare
from assopy.utils import get_user_account_from_email
from p3.models import TicketConference

from conference.fares import (
    FARE_CODE_TYPES,
    FARE_CODE_VARIANTS,
    FARE_CODE_GROUPS,
    FARE_CODE_REGEXES,
)

log = logging.getLogger('conference')


## Forms
#TODO: This monstrosity created a joint modelform for Ticket and TicketConference instances.
#TODO: Use inline form for the one to one relationship or merge the models.
_TICKET_CONFERENCE_COPY_FIELDS = ('shirt_size', 'python_experience', 'diet', 'tagline', 'days', 'badge_image')
def ticketConferenceForm():
    class _(forms.ModelForm):
        class Meta:
            model = TicketConference
            fields = '__all__'

    fields = _().fields

    class TicketConferenceForm(forms.ModelForm):
        shirt_size = fields['shirt_size']
        python_experience = fields['python_experience']
        diet = fields['diet']
        tagline = fields['tagline']
        days = fields['days']
        badge_image = fields['badge_image']

        class Meta:
            model = models.Ticket
            fields = '__all__'

        def __init__(self, *args, **kw):
            if 'instance' in kw:
                o = kw['instance']
                try:
                    p3c = o.p3_conference
                except TicketConference.DoesNotExist:
                    pass
                else:
                    if p3c:
                        initial = kw.pop('initial', {})
                        for k in _TICKET_CONFERENCE_COPY_FIELDS:
                            initial[k] = getattr(p3c, k)
                        kw['initial'] = initial
            return super().__init__(*args, **kw)

    return TicketConferenceForm
##

class ConferenceAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', '_schedule_view', '_attendee_stats')

    def _schedule_view(self, o):
        u = reverse('admin:conference-conference-schedule', args=(o.code,))
        return '<a href="%s">schedule</a>' % u
    _schedule_view.allow_tags = True

    def _attendee_stats(self, o):
        u = reverse('admin:conference-ticket-stats', args=(o.code,))
        return '<a href="%s">Attendee Stats</a>' % u
    _attendee_stats.allow_tags = True

    def get_urls(self):
        admin_view = self.admin_site.admin_view
        urls = [
            re_path(r'^(?P<cid>[\w-]+)/schedule/$',
                admin_view(self.schedule_view),
                name='conference-conference-schedule'),
            re_path(r'^(?P<cid>[\w-]+)/schedule/(?P<sid>\d+)/(?P<tid>\d+)/$',
                admin_view(self.schedule_view_track),
                name='conference-conference-schedule-track'),

            re_path(r'^(?P<cid>[\w-]+)/stats/$',
                admin_view(self.stats_list),
                name='conference-ticket-stats'),
            re_path(r'^(?P<cid>[\w-]+)/stats/details$',
                admin_view(self.stats_details),
                name='conference-ticket-stats-details'),
            re_path(r'^(?P<cid>[\w-]+)/stats/details.csv$',
                admin_view(self.stats_details_csv),
                name='conference-ticket-stats-details-csv'),
        ]
        return urls + super(ConferenceAdmin, self).get_urls()

    def schedule_view_talks(self, conf):
        tids = []
        if conf.code == settings.CONFERENCE_CONFERENCE:
            results = utils.voting_results()
            if results is not None:
                tids = [x[0] for x in results]
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
            tks = sorted(list(sch['tracks'].values()), key=lambda x: x.order)
            tracks.append([ sch['id'], [ t for t in tks ] ])

        return TemplateResponse(
            request,
            'admin/conference/conference/schedule_view.html',
            {
                'conference': conf,
                'tracks': tracks,
                'talks': self.schedule_view_talks(conf),
                'event_form': EventForm(),
            },
        )

    def schedule_view_track(self, request, cid, sid, tid):
        get_object_or_404(models.Track, schedule__conference=cid, schedule=sid, id=tid)
        from datetime import time
        tt = utils.TimeTable2\
            .fromTracks([tid])\
            .adjustTimes(time(8, 00), time(18, 30))
        return TemplateResponse(
            request,
            'admin/conference/conference/schedule_view_schedule.html',
            { 'timetable': tt, },
        )

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
        stats_modules = (
            'p3.stats.tickets_status',
            'p3.stats.conference_speakers',
            'p3.stats.conference_speakers_day',
            'p3.stats.speaker_status',
            'p3.stats.presence_days',
            'p3.stats.shirt_sizes',
            'p3.stats.diet_types',
            'p3.stats.pp_tickets',
        )
        for path in stats_modules:
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
        stats = self.available_stats(cid)

        return TemplateResponse(
            request,
            'admin/conference/conference/attendee_stats.html',
            {
                'conference': cid,
                'stats': stats,
            },
        )

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
        return TemplateResponse(
            request,
            'admin/conference/conference/attendee_stats_details.html',
            {
                'conference': cid,
                'stat': stat,
                'stat_code': '%s.%s' % (sid, rowid),
                'form': form,
                'preview': preview,
                'email_log': settings.CONFERENCE_ADMIN_TICKETS_STATS_EMAIL_LOG,
            },
        )

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

        fname = '[%s] %s.csv' % (settings.CONFERENCE_CONFERENCE, stat['short_description'])
        r = http.HttpResponse(buff.getvalue(), content_type="text/csv")
        r['content-disposition'] = 'attachment; filename="%s"' % fname
        return r


class MultiLingualFormMetaClass(forms.models.ModelFormMetaclass):
    def __new__(mcs, name, bases, attrs):
        new_class = super().__new__(mcs, name, bases, attrs)

        multilingual_fields = new_class.multilingual_fields = []
        model = new_class._meta.model
        if not model:
            return new_class

        for name, f in model.__dict__.items():
            if isinstance(f, ReverseGenericManyToOneDescriptor):
                if f.field.remote_field.model is models.MultilingualContent:
                    multilingual_fields.append(name)

        widget = forms.Textarea
        form_fields = {}
        for field_name in multilingual_fields:
            for lang, _ in settings.LANGUAGES:
                text = forms.CharField(widget=widget, required=False)
                full_name = '{name}_{lang}'.format(name=field_name, lang=lang)
                form_fields[full_name] = text

        new_class.declared_fields.update(form_fields)
        new_class.base_fields.update(form_fields)
        return new_class


class MultiLingualForm(forms.ModelForm, metaclass=MultiLingualFormMetaClass):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

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
            for l, _ in settings.LANGUAGES:
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
        o = super().save(commit=commit)
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
        qs = super().get_queryset(request)
        qs = qs.select_related('user__attendeeprofile')
        if request.GET:
            # Make sure we do an AND query, not an or one as implicit by
            # the Django admin .list_filter
            conf = request.GET.get('talk__conference', None)
            status = request.GET.get('talk__status__exact', None)
            if conf is not None and status is not None:
                qs = qs.filter(talk__conference=conf,
                               talk__status__exact=status)

        qs = qs.filter(user__in=(models.TalkSpeaker.objects\
                #.filter(talk__conference=settings.CONFERENCE_CONFERENCE)\
                .values('speaker')))
        return qs

    def get_paginator(self, request, queryset, per_page, orphans=0, allow_empty_first_page=True):
        sids = queryset.values_list('user', flat=True)
        profiles = dataaccess.profiles_data(sids)
        self._profiles = dict(list(zip(sids, profiles)))
        return super(SpeakerAdmin, self).get_paginator(request, queryset, per_page, orphans, allow_empty_first_page)

    def get_urls(self):
        urls = super(SpeakerAdmin, self).get_urls()
        my_urls = [
            re_path(r'^stats/list/$', self.admin_site.admin_view(self.stats_list), name='conference-speaker-stat-list'),
        ]
        return my_urls + urls

    def stats_list(self, request):
        qs = models.TalkSpeaker.objects\
            .filter(talk__conference=settings.CONFERENCE_CONFERENCE)\
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
        return TemplateResponse(
            request,
            'admin/conference/speaker/stats_list.html',
            {
                'speakers': speakers,
                'groups': groups,
            },
        )

    def _user(self, o):
        if o.user.attendeeprofile:
            p = reverse('profiles:profile', kwargs={'profile_slug': o.user.attendeeprofile.slug})
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


class SponsorIncomeInlineAdmin(admin.TabularInline):
    model = models.SponsorIncome
    extra = 1


class FilterByConference(admin.SimpleListFilter):
    title = 'Conference'
    parameter_name = 'conference'

    def filter_by(self):
        return models.Conference.objects.all().values_list('code', 'name')

    def lookups(self, request, model_admin):
        return self.filter_by()

    def queryset(self, request, qs):
        if self.value() in dict(self.filter_by()):
            return qs.filter(sponsorincome__conference=self.value())


class SponsorAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("sponsor",)}
    list_display = ("sponsor", "url", "conferences")
    search_fields = ["sponsor", "url"]
    inlines = [SponsorIncomeInlineAdmin]
    list_filter = [FilterByConference]

    def conferences(self, obj):
        """List the sponsorised talks by the sponsor"""
        return ", ".join(s.conference for s in obj.sponsorincome_set.all())


class TrackInlineAdmin(admin.TabularInline):
    model = models.Track
    extra = 1


class EventInlineAdmin(admin.TabularInline):
    model = models.Event
    extra = 3


class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('conference', 'slug', 'date')
    inlines = [
        TrackInlineAdmin,
        EventInlineAdmin
    ]

    def get_urls(self):
        urls = super(ScheduleAdmin, self).get_urls()
        v = self.admin_site.admin_view
        my_urls = [
            re_path(r'^stats/$',
                v(self.expected_attendance),
                name='conference-schedule-expected_attendance'),
            re_path(r'^(?P<sid>\d+)/events/$',
                v(self.events),
                name='conference-schedule-events'),
            re_path(r'^(?P<sid>\d+)/events/(?P<eid>\d+)$',
                v(self.event),
                name='conference-schedule-event'),
            re_path(r'^(?P<sid>\d+)/tracks/(?P<tid>[\d]+)$',
                v(self.tracks),
                name='conference-schedule-tracks'),
        ]
        return my_urls + urls

    @common.decorators.render_to_json
    #@transaction.atomic
    def events(self, request, sid):
        sch = get_object_or_404(models.Schedule, id=sid)
        if request.method != 'POST':
            return http.HttpResponseNotAllowed(('POST',))
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
                    .filter(sponsorincome__conference=settings.CONFERENCE_CONFERENCE)\
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
                    .filter(sponsorincome__conference=settings.CONFERENCE_CONFERENCE)\
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
            ctx = {
                'form': form,
                'sid': sid,
                'eid': eid,
            }
            return TemplateResponse(request, 'conference/admin/schedule_event.html', ctx)

    #@transaction.atomic
    def tracks(self, request, sid, tid):
        track = get_object_or_404(models.Track, schedule=sid, id=tid)
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
            ctx = {
                'form': form,
                'sid': sid,
                'tid': tid,
            }
            return TemplateResponse(request, 'conference/admin/schedule_tracks.html', ctx)

    def expected_attendance(self, request):
        allevents = defaultdict(dict)
        for e, info in models.Schedule.objects.expected_attendance(settings.CONFERENCE_CONFERENCE).items():
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
            'schedules': sorted(list(data.items()), key=lambda x: x[0].date),
        }
        return TemplateResponse(request, 'conference/admin/schedule_expected_attendance.html', ctx)


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


class AdminFareForm(forms.ModelForm):
    vat = forms.ModelChoiceField(queryset=Vat.objects.all())

    class Meta:
        model = models.Fare
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance',None)
        if instance:
            try:
                vat = instance.vat_set.all()[0]
                initial = kwargs.get('initial',{})
                initial.update({'vat' : vat })
                kwargs['initial'] = initial
            except  IndexError:
                pass
        super().__init__(*args, **kwargs)


class FareAdmin(admin.ModelAdmin):
    list_display = ('conference', 'code', 'name', 'price', 'recipient_type',
                    'start_validity', 'end_validity', '_vat',)
    list_filter = ('conference',
                   'ticket_type',
                   FilterFareByType,
                   FilterFareByVariant,
                   FilterFareByGroup)
    list_editable = ('price', 'start_validity', 'end_validity')
    list_display_links = ('code', 'name')
    ordering = ('conference', 'start_validity', 'code')
    form = AdminFareForm

    def changelist_view(self, request, extra_context=None):
        if 'conference' not in request.GET and 'conference__exact' not in request.GET:
            q = request.GET.copy()
            q['conference'] = settings.CONFERENCE_CONFERENCE
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(FareAdmin,self).changelist_view(request, extra_context=extra_context)

    def _vat(self,obj):
        try:
            return obj.vat_set.all()[0]
        except IndexError:
            return None
    _vat.short_description = 'VAT'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if 'vat' in form.cleaned_data:
            # se la tariffa viene modificata dalla list_view 'vat' potrebbe
            # non esserci
            vat_fare, created = VatFare.objects.get_or_create(
                fare=obj, defaults={'vat': form.cleaned_data['vat']})
            if not created and vat_fare.vat != form.cleaned_data['vat']:
                vat_fare.vat = form.cleaned_data['vat']
                vat_fare.save()


class TicketAdmin(admin.ModelAdmin):
    list_display = (
        '_name', '_buyer', '_conference', '_ticket', 'ticket_type', 'frozen',
        '_order', '_order_date', '_assigned', '_shirt_size',
        '_diet', '_python_experience',
    )
    search_fields = (
        'name', 'user__first_name', 'user__last_name', 'user__email',
        'orderitem__order__code', 'fare__code',
    )
    list_filter = (
        'fare__conference', 'fare__ticket_type', 'ticket_type', 'fare__code',
        'orderitem__order___complete', 'frozen', 'p3_conference__shirt_size',
        'p3_conference__diet', 'p3_conference__python_experience',
        'orderitem__order__created',
    )
    actions = (
        'do_assign_to_buyer',
        'do_update_ticket_name',
        )

    form = ticketConferenceForm()

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
        """
        Display clickable link to the buyer of the ticket (buyer can be
        different than "assigned" person).
        """
        buyer_user = o.orderitem.order.user.user
        if not (buyer_user.first_name or buyer_user.last_name):
            buyer = buyer_user.email
        else:
            buyer = '%s %s' % (buyer_user.first_name, buyer_user.last_name)
        url = reverse('admin:auth_user_change', args=(buyer_user.id,))
        return mark_safe('<a href="%s">%s</a>' % (url, buyer))
    _buyer.admin_order_field = 'user__first_name'

    def _conference(self, o):
        return o.fare.conference
    _conference.admin_order_field = 'fare__conference'

    def _ticket(self, o):
        return o.fare.code
    _ticket.admin_order_field = 'fare__code'

    def _order(self, obj):
        url = reverse('admin:assopy_order_change',
                      args=(obj.orderitem.order.id,))
        return '<a href="%s">%s</a>' % (url, obj.orderitem.order.code)
    _order.allow_tags = True

    def _order_date(self, o):
        return o.orderitem.order.created
    _order_date.admin_order_field = 'orderitem__order__created'

    def _assigned(self, ticket):
        if ticket.p3_conference:
            assigned_to = ticket.p3_conference.assigned_to
            if assigned_to:
                comment = ''
                user = None
                try:
                    user = get_user_account_from_email(assigned_to)
                except User.MultipleObjectsReturned:
                    comment = ' (email not unique)'
                except User.DoesNotExist:
                    try:
                        user = get_user_account_from_email(assigned_to,
                                                                  active_only=False)
                    except User.DoesNotExist:
                        comment = ' (does not exist)'
                    else:
                        comment = ' (user inactive)'
                if user is not None:
                    url = reverse('admin:auth_user_change', args=(user.id,))
                    user_name = ('%s %s' %
                                 (user.first_name, user.last_name)).strip()
                    if not user_name:
                        user_name = assigned_to
                        comment += ' (no name set)'
                    return '<a href="%s">%s</a>%s' % (url, user_name, comment)
                elif not comment:
                    comment = ' (missing user account)'
                return '%s%s' % (assigned_to, comment)
            else:
                return '(not assigned)'
        else:
            return '(old style ticket)'
    _assigned.allow_tags = True
    _assigned.admin_order_field = 'p3_conference__assigned_to'

    def changelist_view(self, request, extra_context=None):
        if not request.GET:
            q = request.GET.copy()
            q['fare__conference'] = settings.CONFERENCE_CONFERENCE
            q['fare__ticket_type__exact'] = 'conference'
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(TicketAdmin,self).changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super(TicketAdmin, self).get_queryset(request)
        qs = qs.select_related('user', 'fare',)
        return qs

    def get_urls(self):
        urls = super(TicketAdmin, self).get_urls()
        my_urls = [
            re_path(r'^stats/data/$', self.admin_site.admin_view(self.stats_data_view), name='conference-ticket-stats-data'),
        ]
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

            output[c.code] = {
                'data': data,
            }
        return output

    def stats_data_view(self, request):
        output = self.stats_data()
        return http.HttpResponse(json_dumps(output), 'text/javascript')

    def do_assign_to_buyer(self, request, queryset):
        if not queryset:
            self.message_user(request, 'no tickets selected', level='error')
            return
        for ticket in queryset:
            # Assign to buyer
            utils.assign_ticket_to_user(ticket, ticket.user)
    do_assign_to_buyer.short_description = 'Assign to buyer'

    def do_update_ticket_name(self, request, queryset):
        if not queryset:
            self.message_user(request, 'no tickets selected')
            return
        for ticket in queryset:
            # Find selected user
            if not ticket.p3_conference:
                continue
            assigned_to = ticket.p3_conference.assigned_to
            try:
                user = get_user_account_from_email(assigned_to)
            except User.MultipleObjectsReturned:
                self.message_user(request,
                                  'found multiple users with '
                                  'email address %s' % assigned_to,
                                  level='error')
                return
            except User.DoesNotExist:
                self.message_user(request,
                                  'no user record found or user inactive for '
                                  ' email address %s' % assigned_to,
                                  level='error')
                return
            if user is None:
                self.message_user(request,
                                  'no user record found for '
                                  ' email address %s' % assigned_to,
                                  level='error')
            # Reassign to selected user
            utils.assign_ticket_to_user(ticket, user)
    do_update_ticket_name.short_description = 'Update ticket name'

    def _shirt_size(self, o):
        try:
            p3c = o.p3_conference
        except TicketConference.DoesNotExist:
            return ''
        return p3c.shirt_size

    def _diet(self, o):
        try:
            p3c = o.p3_conference
        except TicketConference.DoesNotExist:
            return ''
        return p3c.diet

    def _python_experience(self, o):
        try:
            p3c = o.p3_conference
        except TicketConference.DoesNotExist:
            return ''
        return p3c.python_experience
    _python_experience.admin_order_field = 'p3_conference__python_experience'

    def _tagline(self, o):
        try:
            p3c = o.p3_conference
        except TicketConference.DoesNotExist:
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
        except TicketConference.DoesNotExist:
            p3c = None
        if p3c is None:
            p3c = TicketConference(ticket=obj)

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
            q['frozen__exact'] = 0
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('orderitem__order', 'p3_conference', 'user', 'fare', )
        return qs

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            re_path(r'^stats/data/$', self.admin_site.admin_view(self.stats_data), name='p3-ticket-stats-data'),
        ]
        return my_urls + urls

    def stats_data(self, request):
        from common.jsonify import json_dumps
        from django.db.models import Q
        from collections import defaultdict

        conferences = models.Conference.objects\
            .order_by('conference_start')

        output = {}
        for c in conferences:
            tickets = models.Ticket.objects\
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


            output[c.code] = {
                'data': data,
            }

        return http.HttpResponse(json_dumps(output), 'text/javascript')


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
        my_urls = [
            re_path(r'^merge/$', self.admin_site.admin_view(self.merge_tags), name='conference-conferencetag-merge'),
        ]
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
        url = reverse('admin:conference-conferencetag-merge') + '?' + q.urlencode()
        return http.HttpResponseRedirect(url)
    do_merge_tags.short_description = "Merge the selected tags"

    def merge_tags(self, request):
        if request.method == 'POST':
            tags_id = request.session.get('conference_tag_merge_ids', [])
        else:
            tags_id = list(map(int, request.GET.getlist('tags')))
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
            return http.HttpResponseRedirect(reverse('admin:conference_conferencetag_changelist'))
        else:
            request.session['conference_tag_merge_ids'] = tags_id
        tags = models.ConferenceTag.objects\
            .filter(id__in=tags_id)\
            .order_by_usage()
        ctx = {
            'tags': tags,
        }
        return TemplateResponse(request, 'admin/conference/conferencetag/merge.html', ctx)


class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('datestamp', 'currency', 'rate')


class CaptchaQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'enabled')
    list_filter = ('enabled',)


class NewsAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "conference",
        "get_status_display",
        "created",
        "published_date",
    )
    list_filter = (
        'created',
        'status',
        'published_date',
    )
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ('uuid',)


admin.site.register(models.CaptchaQuestion, CaptchaQuestionAdmin)
admin.site.register(models.Conference, ConferenceAdmin)
admin.site.register(models.ConferenceTag, ConferenceTagAdmin)
admin.site.register(models.ExchangeRate, ExchangeRateAdmin)
admin.site.register(models.Fare, FareAdmin)
admin.site.register(models.Schedule, ScheduleAdmin)
admin.site.register(models.Speaker, SpeakerAdmin)
admin.site.register(models.Sponsor, SponsorAdmin)
admin.site.register(models.Ticket, TicketAdmin)
admin.site.register(models.News, NewsAdmin)
