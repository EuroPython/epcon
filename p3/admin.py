# -*- coding: UTF-8 -*-
from django.contrib import admin
from conference.admin import TicketAdmin
from conference.models import Ticket
from p3 import models

class TicketConferenceAdmin(TicketAdmin):
    list_display = TicketAdmin.list_display + ('_order', '_assigned',)
    
    def _order(self, o):
        return o.orderitem.order.code

    def _assigned(self, o):
        try:
            return o.p3_conference.assigned_to
        except models.TicketConference.DoesNotExist:
            return ''

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
