#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import string
import urllib2
import re
from itertools import izip_longest
import simplejson
import Image, ImageFont, ImageDraw

URL = 'http://assopy.pycon.it/conference/getinfo.py/attendees?column=python_experience'
FONTS = [
    'TradeGothicLTStd-Bold.otf'
]

iFontFirstName = ImageFont.truetype(FONTS[0], 100)
iFontCaption = ImageFont.truetype(FONTS[0], 50)

data = simplejson.loads(urllib2.urlopen(URL).read())
print data['total'], 'attendees'

groups = {
    'staff': [],
    'attendees': [],
}

images = {
    'staff': Image.open('staff.jpg'),
    'd6': Image.open('attendee-6.jpg'),
    'd7': Image.open('attendee-7.jpg'),
    'd67': Image.open('attendee-6-7.jpg'),
}

def getImage(a):
    """
    ritorna l'immagine adatta a seconda del partecipante
    """
    pass

for a in sorted(data['data'], key = lambda x: x['last_name'] + x['first_name']):
    if a['first_name'] + ' ' + a['last_name'] in ('Simone Zinanni', 'Giovanni Bajo', 'Francesco Pallanti', 'Alessia Donzelli'):
        t = 'staff'
    elif a['days'] == '0':
        t = 'd6'
    elif a['days'] == '1':
        t = 'd7'
    elif a['days'] == '0,1':
        t = 'd67'
    else:
        continue
    groups[t].append(a)

for k,v in groups.items():
    print len(v), k

def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)

def wrap_text(font, text, width):
    words = re.split(' ', text)
    lines = [ '' ]
    while words:
        word = words.pop(0)
        line = lines[-1]
        w, h = font.getsize(line + ' ' + word)
        if w <= width:
            lines[-1] += ' ' + word
        else:
            lines.append(word)
    return map(lambda x: x.strip(), lines)

BADGE_WIDTH = 1240
BADGE_HEIGHT = 942
BADGE_OFFSET_Y = 238

def draw_info(d, ix, first_name, last_name, caption, company):
    color = 0, 0, 0
    x, y = 92, ix * (BADGE_HEIGHT + BADGE_OFFSET_Y) + 220
    for c in 0, 1:
        d.text((x + c * BADGE_WIDTH, y), first_name.upper(), font = iFontFirstName, fill = color) 
    x, y = 92, ix * (BADGE_HEIGHT + BADGE_OFFSET_Y) + 330
    for c in 0, 1:
        d.text((x + c * BADGE_WIDTH, y), last_name, font = iFontLastName, fill = color) 

    if company:
        color = 98, 156, 190
        x, y = 92, ix * (BADGE_HEIGHT + BADGE_OFFSET_Y ) + 440
        for c in 0, 1:
            d.text((x + c * BADGE_WIDTH, y), company, font = iFontCaption, fill = color) 

    if caption:
        color = 98, 156, 190
        x, y = 92, ix * (BADGE_HEIGHT + BADGE_OFFSET_Y ) + 520
        for c in 0, 1:
            lines = wrap_text(iFontCaption, caption, BADGE_WIDTH - (98 + 250))
            cy = y
            for l in lines:
                d.text((x + c * BADGE_WIDTH, cy), l, font = iFontCaption, fill = color) 
                cy += iFontCaption.getsize(l)[1] + 8

for t, attendees in groups.items():
    print '%s:' % t, (len(attendees) / 3) + 1, 'pages'
    count = 1
    for block in grouper(3, attendees):
        print '\t page', count
        i = images[t].copy()
        d = ImageDraw.Draw(i)
        for ix, a in enumerate(filter(None, block)):
            draw_info(d, ix, a['first_name'], a['last_name'], a['badge_caption'], a['company_name'])
        i.save('%s-%d.tif' % (t, count))
        count += 1
    
