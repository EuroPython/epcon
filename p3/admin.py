# -*- coding: UTF-8 -*-
from django.contrib import admin
from conference.admin import TicketAdmin
from conference.models import Ticket
from p3 import models

class TicketConferenceAdmin(TicketAdmin):
    list_display = TicketAdmin.list_display + ('_order', '_assigned',)
    list_filter = ('orderitem__order___complete', 'fare__code',)
    
    def _order(self, o):
        return o.orderitem.order.code

    def _assigned(self, o):
        if o.p3_conference:
            return o.p3_conference.assigned_to
        else:
            return ''

    def queryset(self, request):
        qs = super(TicketConferenceAdmin, self).queryset(request)
        qs = qs.select_related('orderitem__order', 'p3_conference', 'user', 'fare', )
        return qs

admin.site.unregister(Ticket)
admin.site.register(Ticket, TicketConferenceAdmin)

class DonationAdmin(admin.ModelAdmin):
    list_display = ('_name', 'date', 'amount')
    list_select_related = True
    search_fields = ('user__user__first_name', 'user__user__last_name', 'user__user__email')
    date_hierarchy = 'date'

    def _name(self, o):
        return o.user.name()
    _name.short_description = 'name'
    _name.admin_order_field = 'user__user__first_name'

admin.site.register(models.Donation, DonationAdmin)
