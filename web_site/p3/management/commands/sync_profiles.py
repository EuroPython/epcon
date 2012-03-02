# -*- coding: UTF-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from assopy import models as amodels
from conference import models as cmodels
from p3 import models

class Command(BaseCommand):
    """
    """
    @transaction.commit_on_success
    def handle(self, *args, **options):
        for u in amodels.User.objects.all().select_related('user'):
            print u.name()
            try:
                profile = cmodels.AttendeeProfile.objects.get(user=u.user)
            except cmodels.AttendeeProfile.DoesNotExist:
                profile = cmodels.AttendeeProfile.objects.getOrCreateForUser(u.user)

            if u.photo:
                try:
                    profile.image.save(u.photo.name, u.photo.file, save=False)
                except IOError:
                    pass
            profile.birthday = u.birthday
            profile.phone = u.phone
            profile.personal_homepage = u.www
            profile.save()

            try:
                p3p  = profile.p3_profile
            except models.P3Profile.DoesNotExist:
                p3p = models.P3Profile(profile=profile)
            p3p.twitter = u.twitter
            if not u.photo:
                url = u.photo_url()
                if 'gravatar.com' in url:
                    p3p.image_gravatar = True
                else:
                    p3p.image_url = url
            p3p.save()
