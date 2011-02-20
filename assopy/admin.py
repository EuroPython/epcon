# -*- coding: UTF-8 -*-
from django.contrib import admin
from assopy import models

class CountryAdmin(admin.ModelAdmin):
    list_display = ('printable_name', 'iso', 'vat_company', 'vat_person')
    list_editable = ('vat_company', 'vat_person')
    search_fields = ('name', 'printable_name', 'iso', 'numcode')

admin.site.register(models.Country, CountryAdmin)

class OrderAdmin(admin.ModelAdmin):
    list_display = ('code', '_user', '_created', '_items')

    def _user(self, o):
        return '%s %s' % (o.user.first_name, o.user.last_name)
    _user.short_description = 'buyer'

    def _items(self, o):
        return o.orderitem_set.count()
    _items.short_description = '#Tickets'

    def _created(self, o):
        return o.created.strftime('%d %b %Y - %H:%M:%S')

admin.site.register(models.Order, OrderAdmin)
