#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import urllib2
import textwrap
import smtplib
from datetime import datetime
import simplejson
from pytz import timezone

try:
    conf_fpath = sys.argv[1]
except IndexError:
    print >> sys.stderr, 'Usage: %s conf_module.py' % (sys.argv[0],)
    sys.exit(1)

conf = {}
try:
    execfile(conf_fpath, {}, conf)
except SyntaxError, e:
    print >> sys.stderr, 'the conf module is incorrect'
    print >> sys.stderr, e
    sys.exit(2)

g = globals()
for key in 'SERVER', 'REPLYTO', 'FROM', 'BODY', 'SUBJECT', 'URL':
    try:
        g[key] = conf[key]
    except KeyError:
        print >> sys.stderr, 'setting %s is missing' % key
        sys.exit(3)

data = simplejson.loads(urllib2.urlopen(URL).read())

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
            print email, '(skipped)'
            continue
        body = BODY % { 'email': email, 'username': username }
        paragraphs = map(lambda p: textwrap.wrap(p, width=72), body.split('\n\n'))
        paragraphs = map(lambda l: '\n'.join(l), paragraphs)
        body = '\n\n'.join(paragraphs)

        email = email.encode('utf-8')
        e = envelope % (email, body.encode('utf-8'))
        print email
        server.sendmail(FROM, [ email ], e)
finally:
    server.quit()
