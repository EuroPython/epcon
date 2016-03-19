# -*- coding: utf-8 -*-
""" Print a json file with the users in the database."""

import json
from   collections import OrderedDict

from   django.core.management.base import BaseCommand, CommandError

from   assopy       import models as assopy_models


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (

    )

    def handle(self, *args, **options):
        db_users = assopy_models.User.objects.all()
        users = OrderedDict()
        for user in db_users:
            #try:
            users[user.id] = {'name': user.name().encode('utf-8'),
                              'assopy_id': user.id,
                             }

            if user.user:
                conf_user = {'id': user.user.id,
                             'username': user.user.get_username().encode('utf-8'),
                             'email': user.user.email.encode('utf-8'),
                             'date-joined': str(user.user.date_joined).encode('utf-8'),
                            }
                users[user.id].update(conf_user)
            #except:
            #    import ipdb; ipdb.set_trace()
            #else:
            print(json.dumps(users, indent=2, separators=(',', ': ')))
