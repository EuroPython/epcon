# -*- coding: UTF-8 -*-
from django.db import models

TICKET_CONFERENCE_SHIRT_SIZES = (
    ('s', 'S'),
    ('m', 'M'),
    ('l', 'L'),
    ('xl', 'XL'),
    ('xxl', 'XXL'),
)
TICKET_CONFERENCE_DIETS = (
    ('omnivorous', 'Omnivorous'),
    ('vegetarian', 'Vegetarian'),
    #('vegan', 'Vegan'),
    #('kosher', 'Kosher'),
)
TICKET_CONFERENCE_EXPERIENCES = (
    (0, '0'),
    (1, '1'),
    (2, '2'),
    (3, '3'),
    (4, '4'),
    (5, '5'),
)
class TicketConference(models.Model):
    ticket = models.OneToOneField('conference.ticket', related_name='p3_conference')
    shirt_size = models.CharField(max_length=2, choices=TICKET_CONFERENCE_SHIRT_SIZES, default='l')
    python_experience = models.PositiveIntegerField(choices=TICKET_CONFERENCE_EXPERIENCES, default=0)
    diet = models.CharField(max_length=10, choices=TICKET_CONFERENCE_DIETS, default='omnivorous')
    tagline = models.CharField(max_length=60, blank=True, help_text='a (funny?) tagline for the attendee')
    assigned_to = models.EmailField(blank=True)

