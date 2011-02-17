# -*- coding: UTF-8 -*-
from django.contrib import admin
from conference.admin import TicketAdmin
from conference.models import Ticket
from p3.models import TicketConference

class TicketConferenceAdmin(TicketAdmin):
    list_display = TicketAdmin.list_display + ('_order', '_assigned',)
    
    def _order(self, o):
        return o.orderitem.order.code

    def _assigned(self, o):
        try:
            return o.p3_conference.assigned_to
        except TicketConference.DoesNotExist:
            return ''

admin.site.unregister(Ticket)
admin.site.register(Ticket, TicketConferenceAdmin)
