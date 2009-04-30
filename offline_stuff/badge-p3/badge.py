#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import string
import urllib2
from itertools import izip_longest
import simplejson
import Image, ImageFont, ImageDraw

URL = 'http://assopy.pycon.it/conference/getinfo.py/attendees'
FONT = 'TradeGothicLTStd-Bold.otf'

iFont = ImageFont.truetype(FONT, 140)
iFontCaption = ImageFont.truetype(FONT, 70)
iAttendees = Image.open('attendee.tif')
#iStaff = 

data = simplejson.loads(urllib2.urlopen(URL).read())

print data['total'], 'attendees'

attendees = []
staff = []

text_jokes = {}
for a in data['data']:
    print a['first_name'], a['last_name'], a['badge_caption']
    if a['username'] in text_jokes:
        a = text_jokes[a['username']](a)
    attendees.append(a)

def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)

BADGE_WIDTH = 824
def draw_name(d, pos, first_name, last_name):
    color = 102, 0, 40
    x, y = pos
    for c in 0, 1:
        d.line([(x + c*BADGE_WIDTH, 0), (x + c*BADGE_WIDTH, 500)], fill = color, width = 1)
        d.text((x + c*BADGE_WIDTH, y), first_name.upper(), font = iFont, fill = color) 
        tw, th = d.textsize(first_name.upper(), font = iFont)
        d.text((x + c*BADGE_WIDTH, y + th - 40), string.capwords(last_name), font = iFont, fill = color)

def draw_caption(d, pos, caption):
    color = 50, 60, 88
    x, y = pos
    for c in 0, 1:
        d.text((x + c*BADGE_WIDTH, y), caption.upper(), font = iFontCaption, fill = color) 

count = 1
for block in grouper(4, attendees):
    print 'block', count
    i = iAttendees.copy()
    d = ImageDraw.Draw(i)
    for ix, a in enumerate(block):
        draw_name(d, (90, 480), a['first_name'], a['last_name'])
        if a['badge_caption']:
            draw_caption(d, (90, 800), a['badge_caption'])
        break
    i.save('foo.tif')
    break
    count += 1
    
