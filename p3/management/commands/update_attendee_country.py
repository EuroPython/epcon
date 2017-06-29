# -*- coding: UTF-8 -*-
from django.core.management.base import BaseCommand, CommandError
from p3 import models
from assopy import utils
import time

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        try:
            email = args[0]
        except IndexError:
            qs = models.P3Profile.objects\
                .filter(country='')\
                .exclude(profile__location='')\
                .select_related('profile__user')
        else:
            qs = models.P3Profile.objects\
                .filter(profile__user__email=email)\
                .select_related('profile__user')
        
        for p in qs:
            c = utils.geocode_country(p.profile.location)
            print p.profile.user.email, '-', p.profile.location, '->', c
            p.country = c
            p.save()
            time.sleep(1)
