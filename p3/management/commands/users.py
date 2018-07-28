# -*- coding: utf-8 -*-
""" Print a json file with the users in the database."""

import json
import logging as log
from   collections import OrderedDict

from   django.core.management.base import BaseCommand

from   assopy       import models as assopy_models


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (

    )

    def handle(self, *args, **options):
        db_users = assopy_models.User.objects.all()
        users = OrderedDict()
        for u in db_users:
            try:
                user_name = u.name()
                user_id   = u.user.id
            except:
                log.error('Error with user {}.'.format(u.id))
                users[u.id] = {'assopy_id': u.id,}
            else:
                users[u.id] = {'name': user_name.encode('utf-8'),
                               'assopy_id': u.id,
                               'id': user_id,
                               'username': u.user.get_username().encode('utf-8'),
                               'email': u.user.email.encode('utf-8'),
                               'date-joined': str(u.user.date_joined).encode('utf-8'),
                               }

        print(json.dumps(users, indent=2, separators=(',', ': ')))
