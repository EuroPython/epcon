# -*- coding: UTF-8 -*-
from django.conf import settings as dsettings
from django.core.cache import cache
from django.core.mail import send_mail as real_send_mail

from conference import models
from conference import settings

import os.path
import re
import subprocess
import urllib2
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

def latest_tweets(screen_name, count):
    import twitter
    key = 'conf:latest:tweets:%s:%s' % (screen_name, count)
    data = cache.get(key)
    if data is None:
        client = twitter.Api()
        # il modulo twitter fornisce un meccanismo di caching, ma
        # preferisco disabilitarlo per due motivi:
        #
        # 1. voglio usare la cache di django, in questo modo modificando i
        # settings modifico anche la cache per twitter
        # 2. di default, ma è modificabile con le api pubbliche, la cache
        # del modulo twitter è file-based e sbaglia a decidere la directory
        # in cui salvare i file; finisce per scrivere in
        # /tmp/python.cache_nobody/... che non è detto sia scrivibile
        # (sopratutto se la directory è stata creata da un altro processo
        # che gira con un utente diverso).
        client.SetCache(None)
        try:
            tweets = client.GetUserTimeline(screen_name, count=count)
        except (ValueError, urllib2.HTTPError):
            # ValueError: a volte twitter.com non risponde correttamente, e
            # twitter (il modulo) non verifica. Di conseguenza viene
            # sollevato un ValueError quando twitter (il modulo) tenta
            # parsare un None come se fosse una stringa json.

            # HTTPError: a volte twitter.com non risponde proprio :) (in
            # realtà risponde con un 503)

            # Spesso questi errori durano molto poco, ma per essere gentile
            # con twitter cacho un risultato nullo per poco tempo.
            tweets = []
        except:
            # vista la stabilità di twitter meglio cachare tutto per
            # evitare errori sul nostro sito
            tweets = []
        data = [{
                    "text": tweet.GetText(),
                    "timestamp": tweet.GetCreatedAtInSeconds(),
                    "followers_count": tweet.user.GetFollowersCount(),
                    "id": tweet.GetId(),
                } for tweet in tweets]
        cache.set(key, data, 60 * 5)
    return data
