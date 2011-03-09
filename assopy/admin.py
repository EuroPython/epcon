# -*- coding: UTF-8 -*-
from django.contrib import admin
from assopy import models

class CountryAdmin(admin.ModelAdmin):
    list_display = ('printable_name', 'vat_company', 'vat_company_verify', 'vat_person')
    list_editable = ('vat_company', 'vat_company_verify', 'vat_person')
    search_fields = ('name', 'printable_name', 'iso', 'numcode')

admin.site.register(models.Country, CountryAdmin)

class OrderAdmin(admin.ModelAdmin):
    list_display = ('code', '_user', '_created', 'method', '_items', '_complete', '_total')
    list_select_related = True
    list_filter = ('method',)
    search_fields = ('code', 'user__user__first_name', 'user__user__last_name', 'user__user__email')
    date_hierarchy = 'created'

    def _user(self, o):
        return o.user.name()
    _user.short_description = 'buyer'

    def _items(self, o):
        return o.orderitem_set.count()
    _items.short_description = '#Tickets'

    def _created(self, o):
        return o.created.strftime('%d %b %Y - %H:%M:%S')

    def _total(self, o):
        return o.total()

admin.site.register(models.Order, OrderAdmin)

class UserAdmin(admin.ModelAdmin):
    list_display = ('_name', 'phone', 'address', '_identities',)
    list_select_related = True
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'address')

    def _name(self, o):
        return o.name()
    _name.short_description = 'name'
    _name.admin_order_field = 'user__first_name'

    def _identities(self, o):
        return o.identities.count()
    _identities.short_description = '#id'

admin.site.register(models.User, UserAdmin)
