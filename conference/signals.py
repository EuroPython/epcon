# -*- coding: UTF-8 -*-
from django import dispatch

timetable_prepare = dispatch.Signal(providing_args=['timetable', 'tracks', 'events'])

attendees_connected = dispatch.Signal(providing_args=['attendee1', 'attendee2'])

# emesso quando un evento viene prenotato (booked=True) o se viene cancellata
# la prenotazione (booked=False)
event_booked = dispatch.Signal(providing_args=['booked', 'event_id', 'user_id'])
