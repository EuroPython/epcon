# -*- coding: UTF-8 -*-
from django.contrib import admin
from conference.admin import AttendeeAdmin
from conference.models import Attendee
from p3.models import AttendeeProfile

class AttendeeProfileAdmin(AttendeeAdmin):
    list_display = AttendeeAdmin.list_display + ('_assigned',)
    
    def _assigned(self, o):
        try:
            return o.p3_conference.assigned_to
        except AttendeeProfile.DoesNotExist:
            return ''

admin.site.unregister(Attendee)
admin.site.register(Attendee, AttendeeProfileAdmin)
