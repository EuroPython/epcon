# -*- coding: UTF-8 -*-
from django import forms
from django.contrib import admin
from django.conf import settings

import models

class DeadlineAdmin(admin.ModelAdmin):

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
