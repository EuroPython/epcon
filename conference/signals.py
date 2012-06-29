# -*- coding: UTF-8 -*-
from django import dispatch

timetable_prepare = dispatch.Signal(providing_args=['timetable', 'tracks', 'events'])

attendees_connected = dispatch.Signal(providing_args=['attendee1', 'attendee2'])
