#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import string
import urllib2
import re
try:
    from itertools import izip_longest
except ImportError:
    def izip_longest(*args, **kwds):
        from itertools import repeat, chain, izip
        # izip_longest('ABCD', 'xy', fillvalue='-') --> Ax By C- D-
        fillvalue = kwds.get('fillvalue')
        def sentinel(counter = ([fillvalue]*(len(args)-1)).pop):
            yield counter()         # yields the fillvalue, or raises IndexError
        fillers = repeat(fillvalue)
        iters = [chain(it, sentinel(), fillers) for it in args]
        try:
            for tup in izip(*iters):
                yield tup
        except IndexError:
            pass

import simplejson
import Image, ImageFont, ImageDraw

URL = 'http://assopy.pycon.it/conference/getinfo.py/attendees?column=python_experience'
FONTS = [
    'TradeGothicLTStd-Bold.otf'
]

iFontFirstName = ImageFont.truetype(FONTS[0], 160)
iFontSmallFirstName = ImageFont.truetype(FONTS[0], 110)
iFontCaption = ImageFont.truetype(FONTS[0], 70)

#data = simplejson.loads(urllib2.urlopen(URL).read())
data = simplejson.loads(file('missing_attendees').read())
print data['total'], 'attendees'

groups = {
    'staff': [],
    'attendee': [],
}

images = {
    'staff': Image.open('staff.tif'),
    'attendee': Image.open('attendee.tif'),
}

logos = {
    'python': Image.open('logo.png'),
    'qui': Image.open('qui.png'),
    'quo': Image.open('quo.png'),
    'qua': Image.open('qua.png'),
    'perl': Image.open('perl.png'),
    'java': Image.open('java.png'),
}

staff_people = (
    "Giovanni Bajo",
    "Marco Beri",
    "Michele Bertoldi",
    "Enrico Franchi",
    "Alan Franzoni",
    "Nicola Larosa",
    "Lorenzo Mancini",
    "Alex Martelli",
    "Stefano Masini",
    "C8E Carlo Miron",
    "David Mugnai",
    "Lawrence Oluyede",
    "Francesco Pallanti",
    "Manlio Perillo",
    "Fabio Pliger",
    "Giovanni Porcari",
    "Michele Simionato",
    "Daniele Varrazzo",
    "Valentino Volonghi",
    "Simone Zinanni",
)

def select_logo(a):
    name = a['first_name'] + ' ' + a['last_name']
    if name == 'Nicola Larosa':
        return logos['qua']
    elif name == 'Marco Beri':
        return logos['qui']
    elif name == 'C8E Carlo Miron':
        return logos['quo']
    elif name == 'Guido van Rossum':
        return logos['perl']
    elif name == 'Emanuele Gesuato':
        # prima che me lo chiediate, no! non lo so chi sia,
        # so solo che ha messo java developer come caption 
        # per il badge.
        return logos['java']
    else:
        return logos['python']

for a in sorted(data['data'], key = lambda x: x['last_name'] + x['first_name']):
    if a['first_name'] + ' ' + a['last_name'] in staff_people:
        t = 'staff'
    else:
        t = 'attendee'
    groups[t].append(a)

#groups['staff'].append({
#    'first_name': 'Simone',
#    'last_name': 'Zinanni',
#    'badge_caption': 'CEO, Develer Srl',
#    'python_experience': 1,
#})
#groups['attendee'].append({
#    'first_name': 'Lorenzo',
#    'last_name': 'Baglioni',
#    'badge_caption': 'easy maker',
#    'python_experience': 1,
#})
#groups['attendee'].append({
#    'first_name': 'Rosy',
#    'last_name': '',
#    'badge_caption': 'hostess',
#    'python_experience': -1,
#})
#groups['attendee'].append({
#    'first_name': 'Luisa',
#    'last_name': '',
#    'badge_caption': 'hostess',
#    'python_experience': -1,
#})
#groups['attendee'].append({
#    'first_name': 'Michela',
#    'last_name': '',
#    'badge_caption': 'hostess',
#    'python_experience': -1,
#})

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

BADGE_WIDTH = 1772 / 2
BADGE_HEIGHT = 1300
BADGE_OFFSET_X = 23
BADGE_OFFSET_Y = 22

def draw_info(i, ix, first_name, last_name, caption, experience, logo):
    if ix <= 1:
        row = 0
    else:
        row = 1

    if ix % 2 == 0:
        col = 0
    else:
        col = 1

    d = ImageDraw.Draw(i)
    if iFontFirstName.getsize(first_name.upper())[0] > BADGE_WIDTH - 64 or iFontFirstName.getsize(last_name)[0] > BADGE_WIDTH - 64:
        fontName = iFontSmallFirstName
        fontOffset = 110
    else:
        fontName = iFontFirstName
        fontOffset = 160
    color = 102, 0, 40
    x, y = 32 + col * (2 * BADGE_WIDTH + BADGE_OFFSET_X), row * (BADGE_HEIGHT + BADGE_OFFSET_Y) + 440
    for c in 0, 1:
        cx = x + c * BADGE_WIDTH
        d.text((cx, y), first_name.upper(), font = fontName, fill = color) 

    x, y = 32 + col * (2 * BADGE_WIDTH + BADGE_OFFSET_X), row * (BADGE_HEIGHT + BADGE_OFFSET_Y) + 440 + fontOffset
    for c in 0, 1:
        cx = x + c * BADGE_WIDTH
        d.text((cx, y), last_name, font = fontName, fill = color) 

    if caption and caption.lower() not in ('sig', 'sig.', 'ing', 'ing.', 'mr', 'mr.', 'mrs', 'mrs.'):
        color = 50, 61, 89
        x, y = 32 + col * (2 * BADGE_WIDTH + BADGE_OFFSET_X), row * (BADGE_HEIGHT + BADGE_OFFSET_Y) + 760
        for c in 0, 1:
            cx = x + c * BADGE_WIDTH
            lines = wrap_text(iFontCaption, caption, BADGE_WIDTH - 64)
            cy = y
            for l in lines:
                d.text((cx, cy), l, font = iFontCaption, fill = color) 
                cy += iFontCaption.getsize(l)[1] + 8
    if experience is not None and experience > -1:
        x, y = 32 + col * (2 * BADGE_WIDTH + BADGE_OFFSET_X), row * (BADGE_HEIGHT + BADGE_OFFSET_Y) + 945
        for c in 0, 1:
            ex = cx = x + c * BADGE_WIDTH
            for p in range(experience + 1):
                i.paste(logo.copy(), (ex, y))
                ex += logo.size[0] + 5

for t, attendees in groups.items():
    print '%s:' % t, (len(attendees) / 4) + 1, 'pages'
    count = 1
    for block in grouper(4, attendees):
        print '\t page', count
        i = images[t].copy()
        for ix, a in enumerate(filter(None, block)):
            draw_info(i, ix, a['first_name'], a['last_name'], a['badge_caption'], a['python_experience'], select_logo(a))
        i.save('%s-%d.tif' % (t, count))
        count += 1

