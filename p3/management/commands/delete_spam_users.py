# -*- coding: utf-8 -*-
""" Delete users creating by spambots.

"""
from optparse import make_option
from django.core.management.base import BaseCommand
from django.db import transaction
from assopy import models as amodels

###

class Command(BaseCommand):

    # Options
    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
                    action='store_true',
                    dest='dry_run',
                    help='Do everything except delete users',
                    ),
    )

    args = '<conference>'

    # Dry run ?
    dry_run = False

    @transaction.atomic
    def handle(self, *args, **options):

	# Handle options    
        self.dry_run = options.get('dry_run', False)

        # Between June 1-4 2018, a Chinese spammer create 30k fake user
        # accounts
        spam_users = amodels.User.objects.filter(
            user__first_name = '金诚送38元',
        )
        print ('Found %i (potential) spam users.' % len(spam_users))
        
        count = 0
        for user in spam_users:
        
            # Filter out users with tickets
            tickets = user.tickets()
            if tickets:
                print ('Spam user %r has %i tickets: skipping.' % (
                    user.user.get_username(), len(tickets)))
                continue
                
            # Delete user and all related objects
            if not self.dry_run:
                # Deleting the Django user will delete the assopy user
                # as well, but not the other way around !
                user.user.delete()
            count += 1
            if count % 1000 == 0:
                print ('Deleted %i spam users.' % count)
        
        if self.dry_run:
            print ('Would have deleted %i spam users.' % count)
        else:
            print ('Deleted %i spam users.' % count)
