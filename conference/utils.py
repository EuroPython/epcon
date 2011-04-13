# -*- coding: UTF-8 -*-
from django.conf import settings as dsettings
from django.core.mail import send_mail as real_send_mail

from conference import models
from conference import settings

import re
import os.path
import subprocess
from collections import defaultdict

def send_email(force=False, *args, **kwargs):
    if force is False and not settings.SEND_EMAIL_TO:
        return
    if 'recipient_list' not in kwargs:
        kwargs['recipient_list'] = settings.SEND_EMAIL_TO
    if 'from_email' not in kwargs:
        kwargs['from_email'] = dsettings.DEFAULT_FROM_EMAIL
    real_send_mail(*args, **kwargs)

def ranking_of_talks(talks, missing_vote=5):
    import conference
    vengine = os.path.join(os.path.dirname(conference.__file__), 'utils', 'voteengine-0.99', 'voteengine.py')
    talks_map = dict((t.id, t) for t in talks)
    cands = ' '.join(map(str, talks_map.keys()))
    tie = ' '.join(str(t.id) for t in sorted(talks, key=lambda x: x.created))
    vinput = [
        '-m schulze',
        '-cands %s -tie %s' % (cands, tie),
    ]

    votes = models.VotoTalk.objects.filter(talk__in=talks).order_by('user', '-vote')
    users = defaultdict(lambda: defaultdict(list)) #dict((t.id, 5) for t in talks))
    for vote in votes:
        users[vote.user_id][vote.vote].append(vote.talk_id)

    talks_ids = set(t.id for t in talks)
    for votes in users.values():
        missing_talks = talks_ids - set(sum(votes.values(), []))
        votes[missing_vote].extend(missing_talks)

        ballot = sorted(votes.items(), reverse=True)
        input_line = []
        for vote, talks in ballot:
            input_line.append('='.join(map(str, talks)))
        vinput.append('>'.join(input_line))

    pipe = subprocess.Popen([ vengine ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    out, err = pipe.communicate('\n'.join(vinput))

    return [ talks_map[int(tid)] for tid in re.findall(r'\d+', out.split('\n')[-2]) ]
