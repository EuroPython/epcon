# -*- coding: UTF-8 -*-
from __future__ import absolute_import

from django import forms
from django import http
from django import template
from django.contrib import admin
from django.conf import settings as dsettings
from django.conf.urls.defaults import url, patterns
from django.core import urlresolvers
from django.db import transaction
from django.shortcuts import redirect, render_to_response

from conference import dataaccess
from conference import models
from conference import settings
from conference import utils

import csv
import logging
import re
from collections import defaultdict
from cStringIO import StringIO

log = logging.getLogger('conference')

class ConferenceAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')

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

    def get_form(self, request, obj=None, **kwargs):
        form = super(DeadlineAdmin, self).get_form(request, obj, **kwargs)
        if obj:
            contents = dict((c.language, (c.headline, c.body)) for c in obj.deadlinecontent_set.all())
        for l, _ in dsettings.LANGUAGES:
            f = forms.CharField(max_length=200, required=False)
            if obj:
                try:
                    f.initial = contents[l][0]
                except:
                    pass
            form.base_fields['headline_' + l] = f
            f = forms.CharField(widget=forms.Textarea, required=False)
            if obj:
                try:
                    f.initial = contents[l][1]
                except:
                    pass
            form.base_fields['body_' + l] = f
        return form

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
from django.contrib.contenttypes import generic

class MultiLingualAdminContent(admin.ModelAdmin):

    multilingual_widget = forms.Textarea
    
    def _get_relation_field(self):
        for name, f in self.model.__dict__.items():
            if isinstance(f, generic.ReverseGenericRelatedObjectsDescriptor):
                if f.field.related.parent_model is models.MultilingualContent:
                    yield name

    def get_form(self, request, obj=None, **kwargs):
        form = super(MultiLingualAdminContent, self).get_form(request, obj, **kwargs)
        for field_name in self._get_relation_field():
            if obj:
                contents =  dict(
                    (c.language, c.body) for c in getattr(obj, field_name).all() if c.content == field_name
                )
            for l, _ in dsettings.LANGUAGES:
                text = forms.CharField(widget=self.multilingual_widget, required=False)
                if obj:
                    text.initial = contents.get(l, '')
                form.base_fields['%s_%s' % (field_name, l)] = text
        return form

    def save_model(self, request, obj, form, change):
        obj.save()
        data = form.cleaned_data
        for field_name in self._get_relation_field():
            if change:
                contents =  dict(
                    (c.language, c) for c in getattr(obj, field_name).all() if c.content == field_name
                )
            for l, _ in dsettings.LANGUAGES:
                key =  '%s_%s' % (field_name, l)
                if change:
                    try:
                        instance = contents[l]
                    except KeyError:
                        instance = models.MultilingualContent()
                else:
                    instance = models.MultilingualContent()
                if not instance.id:
                    instance.content_object = obj
                    instance.language = l
                    instance.content = field_name
                instance.body = data.get(key, '')
                instance.save()

class SpeakerAdminForm(forms.ModelForm):
    class Meta:
        model = models.Speaker

    def __init__(self, *args, **kwargs):
        super(SpeakerAdminForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = self.fields['user'].queryset.order_by('username')

class SpeakerAdmin(MultiLingualAdminContent):
    #prepopulated_fields = {"slug": ("name",)}
    #list_display = ('avatar', 'name', '_email', 'slug')
    #list_display_links = ('name', )
    form = SpeakerAdminForm

    def _email(self, obj):
        return obj.user.email

    def avatar(self, obj):
        if obj.image:
            h = '<img src="%s" alt="%s" height="32" />'
            return h % (obj.image.url, obj.slug)
        else:
            return ''
    avatar.allow_tags = True

admin.site.register(models.Speaker, SpeakerAdmin)

class TalkAdminForm(forms.ModelForm):
    class Meta:
        model = models.Talk

    # per semplificare l'inserimento del video permetto all'utente di inserire
    # il blob html che copia da viddler e da li estraggo la url che mi
    # interessa
    video_check = re.compile(r'http://www\.viddler\.com/player/[^/]+/?')

    def clean_video(self):
        match = self.video_check.search(self.cleaned_data['video'])
        if match:
            self.cleaned_data['video'] = match.group(0)
        else:
            self.cleaned_data['video'] = ''
        return self.cleaned_data['video']

class TalkAdmin(MultiLingualAdminContent):
    actions = ('do_accept_talks_in_schedule', 'do_speakers_data',)
    list_display = ('title', 'conference', '_speakers', 'duration', 'status', '_slides', '_video')
    list_editable = ('status',)
    list_filter = ('conference', 'status',)
    ordering = ('-conference', 'title')
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ('title',)

    form = TalkAdminForm

    def get_paginator(self, request, queryset, per_page, orphans=0, allow_empty_first_page=True):
        # utilizzo dataaccess per fare una sola query verso il db, in questo
        # modo ho subito tutti i dati pronti (utile ad esempio per mostrare i
        # nomi degli speaker)
        talks = dataaccess.talks_data(queryset.values_list('id', flat=True))
        self.cached_talks = dict([(x['talk'].id, x) for x in talks])
        sids = [ s['id'] for t in talks for s in t['speakers'] ]
        speakers = dataaccess.speakers_data(sids)
        self.cached_speakers = dict([(x['speaker'].id, x) for x in speakers])
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
                'mail': self.cached_speakers[x['id']]['speaker'].user.email,
            }
            output.append('<a href="%(url)s">%(name)s</a> (<a href="mailto:%(mail)s">mail</a>)' % args)
        return '<br />'.join(output)
    _speakers.allow_tags = True

    def _slides(self, obj):
        return bool(obj.slides)
    _slides.boolean = True

    def _video(self, obj):
        return bool(obj.video_type) and (bool(obj.video_url) or bool(obj.video_file))
    _video.boolean = True

    @transaction.commit_on_success
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
                writer.writerow((t.status, t.title.encode('utf-8'), s.name.encode('utf-8'), s.user.email.encode('utf-8') if s.user else ''))
        response = http.HttpResponse(buff.getvalue(), mimetype="text/csv")
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
        """
        Elenca le conferenze sponsorizzate dallo sponsor
        """
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
        """
        Elenca le conferenze a cui il partner ha partecipato
        """
        return ', '.join(s.conference for s in obj.mediapartnerconference_set.all())

admin.site.register(models.MediaPartner, MediaPartnerAdmin)

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
        my_urls = patterns('',
            url(r'^stats/$', self.admin_site.admin_view(self.expected_attendance), name='conference-schedule-expected_attendance'),
        )
        return my_urls + urls

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

class DidYouKnowAdmin(MultiLingualAdminContent):
    list_display = ('_message', 'visible')
    
    def _message(self, o):
        messages = dict( (c.language, c) for c in o.messages.all() if c.body)
        try:
            return messages[dsettings.LANGUAGES[0][0]].body
        except KeyError:
            if messages:
                return messages.values()[0].body
            else:
                return ''

admin.site.register(models.DidYouKnow, DidYouKnowAdmin)

class QuoteAdmin(MultiLingualAdminContent):
    list_display = ('who', 'conference', '_text')
    
    def _text(self, o):
        return o.text[:80]

admin.site.register(models.Quote, QuoteAdmin)

class SpecialPlaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'email')
    
admin.site.register(models.SpecialPlace, SpecialPlaceAdmin)

class FareAdmin(admin.ModelAdmin):
    list_display = ('conference', 'code', 'name', 'price', 'recipient_type', 'start_validity', 'end_validity')
    list_filter = ('conference', )
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
    list_editable = ('ticket_type',)
    search_fields = ('name', 'user__first_name', 'user__last_name', 'user__email')
    if settings.TICKET_BADGE_ENABLED:
        actions = ('do_ticket_badge',)

    def _name(self, o):
        if o.name:
            return o.name
        else:
            return self._buyer(o)

    def _buyer(self, o):
        return '%s %s' % (o.user.first_name, o.user.last_name)

    def _conference(self, o):
        return o.fare.conference

    def _ticket(self, o):
        return o.fare.code

    def queryset(self, request):
        qs = super(TicketAdmin, self).queryset(request)
        qs = qs.select_related('user', 'fare',)
        return qs

    def do_ticket_badge(self, request, qs):
        files = utils.render_badge(qs)
        if len(files) == 1:
            response = http.HttpResponse(files[0], mimetype="application/x-gzip")
            response['Content-Disposition'] = 'attachment; filename=badge.tar.gz'
        else:
            # TODO zip all the tar files together
            raise RuntimeError()
        return response
    do_ticket_badge.short_description = 'Ticket Badge'

    def get_urls(self):
        urls = super(TicketAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^stats/$', self.admin_site.admin_view(self.stats_list), name='conference-ticket-stats'),
        )
        return my_urls + urls

    def stats(self, conference, stat=None):
        return settings.ADMIN_STATS(conference, stat=stat)

    def stats_list(self, request):
        class FormConference(forms.Form):
            conference = forms.ChoiceField(
                choices=models.Conference.objects.all().values_list('code', 'name'),
                required=False
            )
        form = FormConference(data=request.GET)
        stats = []
        if form.is_valid():
            conference = form.cleaned_data['conference'] or settings.CONFERENCE
            stats = self.stats(conference)
        else:
            stats = []

        ctx = {
            'form': form,
            'conference': conference,
            'stats': stats,
        }
        return render_to_response('conference/admin/ticket_stats.html', ctx, context_instance=template.RequestContext(request))

admin.site.register(models.Ticket, TicketAdmin)

class ConferenceTagAdmin(admin.ModelAdmin):
    actions = ('do_merge_tags',)
    list_display = ('slug', 'name', '_usage',)
    list_editable = ('name',)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ('name',)

    def get_urls(self):
        urls = super(ConferenceTagAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^merge/$', self.admin_site.admin_view(self.merge_tags), name='conference-conferencetag-merge'),
        )
        return my_urls + urls

    def get_paginator(self, request, queryset, per_page, orphans=0, allow_empty_first_page=True):
        self.cached = dataaccess.tags()
        return super(ConferenceTagAdmin, self).get_paginator(request, queryset, per_page, orphans, allow_empty_first_page)
    def _usage(self, o):
        return len(self.cached.get(o, {}))

    def do_merge_tags(self, request, queryset):
        ids = queryset.values_list('id', flat=True)
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

            # Non voglio utilizzare le operazioni bulk per l'update di
            # ConferenceTaggedItem e la cancellazione di ConferenceTag
            # (objects.update, objects.delete) perché la cache gestita da
            # dataaccess si appoggia ai segnali per rimanere coerente.
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
