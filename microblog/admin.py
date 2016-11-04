# -*- coding: UTF-8 -*-
import datetime
from microblog import models
from django import forms
from django.conf import settings
from django.contrib import admin

class PostAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_display = ('headline', 'date', 'author', 'status')
    ordering = ('-date',)

    def headline(self, obj):
        contents = dict((c.language, c) for c in obj.postcontent_set.all())
        for l, lname in settings.LANGUAGES:
            try:
                content = contents[l]
            except KeyError:
                continue
            if content.headline:
                return content.headline
        else:
            return '[No headline]'

    def get_fieldsets(self, request, obj=None, **kwargs):
        fieldsets = super(PostAdmin, self).get_fieldsets(request, obj=obj, **kwargs)
        prepopulated_fields = {}
        for l, lname in settings.LANGUAGES:
            fieldsets.append((
                lname, {
                    'fields': (
                        'headline_' + l,
                        'slug_' + l,
                        'summary_' + l,
                        'body_' + l,
                    )
                }))
            prepopulated_fields['slug_' + l] = ('headline_' + l,)
        self.prepopulated_fields = prepopulated_fields
        return fieldsets

    def get_form(self, request, obj=None, **kwargs):
        contents = {}
        if obj:
            contents = dict([(c.language, c) for c in obj.postcontent_set.all()])
        def getContent(lang, field):
            try:
                return getattr(contents[lang], field, '')
            except KeyError:
                return ''
        class PostForm(forms.ModelForm):
            class Meta:
                model = models.Post
                fields = ('date', 'author', 'status', 'tags', 'category', 'allow_comments', 'featured', 'image')
            def __init__(self, *args, **kw):
                super(PostForm, self).__init__(*args, **kw)
                for lang_code, _ in settings.LANGUAGES:
                    fields = {
                        'headline': forms.CharField(required=False, max_length=200),
                        'slug': forms.CharField(required=False, max_length=50),
                        'summary': forms.CharField(required=False, widget=forms.Textarea),
                        'body': forms.CharField(required=False, widget=forms.Textarea),
                    }
                    for field_name in 'headline', 'slug', 'summary', 'body':
                        f = fields[field_name]
                        f.label = '%s (%s)' % (field_name, lang_code.split('-', 1)[0].upper())
                        f.initial = getContent(lang_code, field_name)
                        self.fields[field_name + '_' + lang_code] = f
                # un po' di valori di default sensati
                self.fields['date'].initial = datetime.datetime.now()
                self.fields['author'].initial = request.user.id

            def clean(self):
                data = self.cleaned_data
                # mi assicuro che se una lingua è stata utilizzata i campi
                # headline, slug e summary devono essere riempiti
                # inoltre mi assicuro che almeno una lingua sia stata usata
                valid_langs = []
                language_fields = 'headline', 'slug', 'summary', 'body'
                needed_fields = set(('headline', 'slug', 'summary'))
                for l, lname in settings.LANGUAGES:
                    lfield = []
                    for fname in language_fields:
                        key = fname + '_' + l
                        if data[key]:
                            lfield.append(fname)
                    if lfield:
                        if needed_fields.intersection(set(lfield)) != needed_fields:
                            raise forms.ValidationError('Se utilizzi una lingua i campi "headline", "slug" e "summary" sono obbligatori')
                        else:
                            valid_langs.append(l)

                if not valid_langs:
                    raise forms.ValidationError('Devi usare almeno una lingua')

                return data
        return PostForm

    def save_model(self, request, obj, form, change):
        obj.save()
        data = form.cleaned_data
        fields = ('headline', 'slug', 'summary', 'body')
        for l, _ in settings.LANGUAGES:
            if change:
                try:
                    instance = models.PostContent.objects.get(post = obj, language = l)
                except models.PostContent.DoesNotExist:
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

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

admin.site.register(models.Category, CategoryAdmin)

