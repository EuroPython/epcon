# -*- coding: UTF-8 -*-
import datetime
from collections import OrderedDict, defaultdict

import simplejson as json
from django import http
from django.conf import settings
from django.shortcuts import redirect, render
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.decorators import login_required

from epcon.p3.render import render_to_json
from epcon.p3.utils import(speaker_companies,
                           speaker_listing,
                           speaker_emails,
                           speaker_twitters,
                           have_tickets,
                           talk_schedule,
                           talk_track_title,
                           talk_votes,
                           group_all_talks_by_admin_type,
                           clean_title,
                           )

@login_required
@render_to_json
def api_schedule(request, conference):
        talks = group_all_talks_by_admin_type(conference, 'accepted')

        sessions = OrderedDict()
        # Print list of submissions
        for type_name, session_talks in talks.items():
            if not session_talks:
                continue

            sessions[type_name] = OrderedDict()
            # Sort by talk title using title case
            session_talks.sort(key=lambda talk:
                               clean_title(talk.title).encode('utf-8').title())

            for talk in session_talks:
                schedule = talk_schedule(talk)

                sessions[type_name][talk.id] = {
                'id':             talk.id,
                #'admin_type':     talk.get_admin_type_display().encode('utf-8'),
                'type':           talk.get_type_display().encode('utf-8'),
                'duration':       talk.duration,
                'level':          talk.get_level_display().encode('utf-8'),
                'track_title':    ', '.join(talk_track_title(talk)).encode('utf-8'),
                'timerange':      ', '.join(schedule).encode('utf-8'),
                'tags':           [str(t) for t in talk.tags.all()],
                'url':            u'https://{}.europython.eu/{}'.format(conference, talk.get_absolute_url()).encode('utf-8'),
                'tag_categories': [tag.category.encode('utf-8') for tag in talk.tags.all()],
                'sub_community':  talk.p3_talk.sub_community.encode('utf-8'),
                'title':          clean_title(talk.title).encode('utf-8'),
                'sub_title':      clean_title(talk.sub_title).encode('utf-8'),
                'language':       talk.get_language_display().encode('utf-8'),
                #'abstract_long':  [abst.body.encode('utf-8') for abst in talk.abstracts.all()],
                'abstract_short': talk.abstract_short.encode('utf-8'),
                'abstract_extra': talk.abstract_extra.encode('utf-8'),
                'speakers':       u', '.join(speaker_listing(talk)).encode('utf-8'),
                'companies':      u', '.join(speaker_companies(talk)).encode('utf-8'),
                'emails':         u', '.join(speaker_emails(talk)).encode('utf-8'),
                'twitters':       u', '.join(speaker_twitters(talk)).encode('utf-8'),
                }

        return ``json.dumps(sessions, indent=2)
