# -*- coding: utf-8 -*-
from django import dispatch

timetable_prepare = dispatch.Signal(providing_args=['timetable', 'tracks', 'events'])

attendees_connected = dispatch.Signal(providing_args=['attendee1', 'attendee2'])

# Issued when an event is booked (booked = True) or if the booking is canceled (booked=False)
event_booked = dispatch.Signal(providing_args=['booked', 'event_id', 'user_id'])
