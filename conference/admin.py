# -*- coding: UTF-8 -*-
from __future__ import absolute_import

from django import forms
from django.contrib import admin
from django.conf import settings

from conference import models

class DeadlineAdmin(admin.ModelAdmin):

    list_display = ('date', 'text', 'isValid')

    def text(self, obj):
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
    text.short_description = 'testo'
    text.allow_tags = True

    def isValid(self, obj):
        return not obj.isExpired()
    isValid.boolean = True

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
            contents = dict((c.language, c.body) for c in obj.deadlinecontent_set.all())
        for l, _ in settings.LANGUAGES:
            f = forms.CharField(widget = forms.Textarea, required = False)
            if obj:
                f.initial = contents.get(l, '')
            form.base_fields['body_' + l] = f
        return form

    def save_model(self, request, obj, form, change):
        obj.save()
        data = form.cleaned_data
        for l, _ in settings.LANGUAGES:
            key =  'body_' + l
            if change:
                try:
                    instance = models.DeadlineContent.objects.get(deadline = obj, language = l)
                except models.DeadlineContent.DoesNotExist:
                    instance = models.DeadlineContent()
            else:
                instance = models.DeadlineContent()
            if not instance.id:
                instance.deadline = obj
                instance.language = l
            instance.body = data.get(key, '')
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
                contents =  dict((c.language, c.body) for c in getattr(obj, field_name).all())
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
                contents =  dict((c.language, c) for c in getattr(obj, field_name).all())
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

class TalkAdmin(MultiLingualAdminContent):
    prepopulated_fields = {"slug": ("title",)}
    list_display = ('title', '_speakers')
    
    def _speakers(self, obj):
        return ' ,'.join((s.name for s in obj.speakers.all()))

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

class TrackInlineAdmin(admin.TabularInline):
    model = models.Track
    extra = 1

class EventInlineAdmin(admin.TabularInline):
    model = models.Event
    extra = 2

class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('conference', 'slug', 'date')
    inlines = [
        TrackInlineAdmin,
        EventInlineAdmin
    ]

admin.site.register(models.Schedule, ScheduleAdmin)
