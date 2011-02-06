# -*- coding: UTF-8 -*-

from django.contrib import admin
from assopy import models

class CountryAdmin(admin.ModelAdmin):
    list_display = ('printable_name', 'iso', 'vat_company', 'vat_person')
    list_editable = ('vat_company', 'vat_person')
    search_fields = ('name', 'printable_name', 'iso', 'numcode')

admin.site.register(models.Country, CountryAdmin)
