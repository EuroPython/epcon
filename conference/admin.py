# -*- coding: UTF-8 -*-
from __future__ import absolute_import

from django import forms
from django.contrib import admin
from django.conf import settings

from conference import models

import re

class ConferenceAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')

admin.site.register(models.Conference, ConferenceAdmin)

class DeadlineAdmin(admin.ModelAdmin):

    list_display = ('date', '_headline', '_text', '_expired')

    def _headline(self, obj):
        contents = dict((c.language, c) for c in obj.deadlinecontent_set.all())
        for l, lname in settings.LANGUAGES:
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
        for l, lname in settings.LANGUAGES:
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
        for l, _ in settings.LANGUAGES:
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
        for l, _ in settings.LANGUAGES:
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
    
    def _get_relation_field(self):
        for name, f in self.model.__dict__.items():
            if isinstance(f, generic.ReverseGenericRelatedObjectsDescriptor):
                yield name

    def get_form(self, request, obj=None, **kwargs):
        form = super(MultiLingualAdminContent, self).get_form(request, obj, **kwargs)
        for field_name in self._get_relation_field():
            if obj:
                contents =  dict(
                    (c.language, c.body) for c in getattr(obj, field_name).all() if c.content == field_name
                )
            for l, _ in settings.LANGUAGES:
                text = forms.CharField(widget = forms.Textarea, required = False)
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
            for l, _ in settings.LANGUAGES:
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

class SpeakerAdmin(MultiLingualAdminContent):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('avatar', 'name', 'slug')
    list_display_links = ('name', )

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
    prepopulated_fields = {"slug": ("title",)}
    list_display = ('title', 'conference', '_speakers', 'duration', '_slides', '_video')
    list_filter = ('conference', )
    search_fields = ('title',)
    ordering = ('-conference', 'title')

    form = TalkAdminForm
    
    def _speakers(self, obj):
        main = ', '.join((s.name for s in obj.speakers.all()))
        additional = ','.join((s.name for s in obj.additional_speakers.all()))
        if additional:
            return '%s [%s]' % (main, additional)
        else:
            return main

    def _slides(self, obj):
        return bool(obj.slides)
    _slides.boolean = True

    def _video(self, obj):
        return bool(obj.video_type) and (bool(obj.video_url) or bool(obj.video_file))
    _video.boolean = True

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
            return messages[settings.LANGUAGES[0][0]].body
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
    list_display = ('conference', 'code', 'name', 'price', 'start_validity', 'end_validity')
    
admin.site.register(models.Fare, FareAdmin)

class TicketAdmin(admin.ModelAdmin):
    list_display = ('_name', '_buyer', '_conference', '_ticket')

    def _name(self, o):
        if o.name:
            return o.name
        else:
            return self._buyer(o)

    def _buyer(self, o):
        return '%s %s' % (o.user.first_name, o.user.last_name)

    def _conference(self, o):
        return o.ticket.conference

    def _ticket(self, o):
        return o.ticket.code

admin.site.register(models.Ticket, TicketAdmin)
