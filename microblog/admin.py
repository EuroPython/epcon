# -*- coding: UTF-8 -*-
import datetime

from django import forms
from django.contrib import admin
from django.conf import settings

import models

class PostAdmin(admin.ModelAdmin):
    
    date_hierarchy = 'date'
    list_display = ('date', 'author', 'status')

    def get_fieldsets(self, request, obj=None, **kwargs):
        fieldsets = [
            (None, {
                'fields': ('date', 'author', 'status', 'tags', 'allow_comments')
            })
        ]
        prepopulated_fields = {}
        lang_fieldsets = {}
        for l, lname in settings.LANGUAGES:
            f = (lname, { 'fields': [] } )
            lang_fieldsets[l] = f[1]
            fieldsets.append(f)
            prepopulated_fields['slug_' + l] = ('headline_' + l,)
        self.prepopulated_fields = prepopulated_fields

        form = self.get_form(request, obj)
        for name in form.base_fields:
            if '_' not in name:
                continue
            l = name.rsplit('_', 1)[1]
            if len(l) > 3:
                # houch, allow_comments ha l'_
                continue
            lang_fieldsets[l]['fields'].append(name)
        return fieldsets

    def get_form(self, request, obj=None, **kwargs):
        form = super(PostAdmin, self).get_form(request, obj, **kwargs)
        if obj:
            contents = dict((c.language, c) for c in obj.postcontent_set.all())
        def getContent(lang, field):
            try:
                return getattr(contents[lang], field, '')
            except KeyError:
                return ''
        # a differenza delle deadline qui devo aggiungere 4 campi
        #   headline
        #   slug
        #   summary
        #   body
        for l, _ in settings.LANGUAGES:
            fields = {
                'headline': forms.CharField(required = False, max_length = 200),
                'slug': forms.CharField(required = False, max_length = 50),
                'summary': forms.CharField(required = False, widget = forms.Textarea),
                'body': forms.CharField(required = False, widget = forms.Textarea),
            }
            for k in 'headline', 'slug', 'summary', 'body':
                f = fields[k]
                if obj:
                    f.initial = getContent(l, k)
                form.base_fields[k + '_' + l] = f
        # un po' di valori di default sensati
        form.base_fields['date'].initial = datetime.datetime.now()
        form.base_fields['author'].initial = request.user.id
        return form

    def save_model(self, request, obj, form, change):
        obj.save()
        data = form.cleaned_data
        fields = ('headline', 'slug', 'summary', 'body')
        for l, _ in settings.LANGUAGES:
            if change:
                try:
                    instance = models.PostContent.objects.get(post = obj, language = l)
                except models.DeadlineContent.DoesNotExist:
                    instance = models.PostContent()
            else:
                instance = models.PostContent()
            if not instance.id:
                instance.post = obj
                instance.language = l
            for f in fields:
                key = f + '_' + l
                setattr(instance, f, data.get(key, ''))
            instance.save()

admin.site.register(models.Post, PostAdmin)
