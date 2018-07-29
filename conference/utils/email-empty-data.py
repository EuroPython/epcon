#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import urllib.request, urllib.error, urllib.parse
import textwrap
import smtplib
from datetime import datetime
import simplejson
from pytz import timezone

try:
    conf_fpath = sys.argv[1]
except IndexError:
    print('Usage: %s conf_module.py' % (sys.argv[0],), file=sys.stderr)
    sys.exit(1)

conf = {}
try:
    exec(compile(open(conf_fpath).read(), conf_fpath, 'exec'), {}, conf)
except SyntaxError as e:
    print('the conf module is incorrect', file=sys.stderr)
    print(e, file=sys.stderr)
    sys.exit(2)

g = globals()
for key in 'SERVER', 'REPLYTO', 'FROM', 'BODY', 'SUBJECT', 'URL':
    try:
        g[key] = conf[key]
    except KeyError:
        print('setting %s is missing' % key, file=sys.stderr)
        sys.exit(3)

data = simplejson.loads(urllib.request.urlopen(URL).read())

now = timezone('Europe/Rome').localize(datetime.now())

envelope = """\
From: %(from)s
To: %%s
Subject: %(subject)s
Reply-To: %(reply)s
Date: %(date)s
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit

%%s
""" % { 'from': FROM, 'subject': SUBJECT, 'reply': REPLYTO, 'date': now.strftime('%a, %d %b %Y %H:%M:%S %z') }

skip_email = []
server = smtplib.SMTP(SERVER)
try:
    for email, username in data['data']:
        if not email or not username:
            continue
        if email in skip_email:
            print(email, '(skipped)')
            continue
        body = BODY % { 'email': email, 'username': username }
        paragraphs = [textwrap.wrap(p, width=72) for p in body.split('\n\n')]
        paragraphs = ['\n'.join(l) for l in paragraphs]
        body = '\n\n'.join(paragraphs)

        email = email
        e = envelope % (email, body)
        print(email)
        server.sendmail(FROM, [ email ], e)
finally:
    server.quit()
