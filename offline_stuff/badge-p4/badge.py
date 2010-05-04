#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import math
import re
import string
import sys
import urllib2
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

URL = 'http://assopy.pycon.it/conference/getinfo/attendees_q?event=pycon4&column=python_experience'

FONT_NAME = 'League Gothic.otf'
FONTS = {
    'name': ImageFont.truetype(FONT_NAME, 36 * 4.16),
    'name_small': ImageFont.truetype(FONT_NAME, 30 * 4.16),
    'info': ImageFont.truetype(FONT_NAME, 18 * 4.16),
}

MM2INCH = 0.03937
DPI = 300
PAGE_SIZE = map(int, (490 * MM2INCH * DPI, 318 * MM2INCH * DPI))
RESIZE = None
BADGE_PER_PAGE = 9
BADGE = {
    'width': 1724 / 2,
    'height': 1251,
    'first_name': (70, 1251 - 830),
    'last_name': (70, 1251 - 700),
    'info': (70, 1251 - 420),
    'experience': (70, 1251 - 530),
    'abbondanza': 3 * MM2INCH * DPI,
}

groups = {
    'staff': {
        'image': Image.open('Badge Staff.png'),
        'attendees': [],
    },
    'attendee': {
        'image': Image.open('Badge.png'),
        'attendees': [],
    },
}

staff_people = set(map(lambda x: x.lower(), (
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
    "Giulia ",
    "Roxana ",
    "Carolina ",
)))

LOGO = {
    None: Image.open('logo.png'),
    'lorenzo berni': Image.open('apple.png'),
    'andrea righi': Image.open('bertos.png'),
    'luca ottaviano': Image.open('bertos.png'),
    'francesco sacchi': Image.open('bertos.png'),
    'francesco pallanti': Image.open('croissant.png'),
    'nicola larosa': Image.open('qua.png'),
    'marco beri': Image.open('qui.png'),
    'c8e carlo miron': Image.open('quo.png'),
    'armin rigo': Image.open('pypy.png'),
    'antonio cuni': Image.open('pypy.png'),
    'lorenzo masini': Image.open('beer.png'),
}

colors = {
    None: {
        'name': (152, 22, 71),
        'info': (76, 95, 95),
    }
}

data = simplejson.loads(urllib2.urlopen(URL).read())
print data['total'], 'attendees'

for a in filter(lambda x: x['username'], data['data']):
    if a['last_name'] is None:
        a['last_name'] = ''
    k = (a['first_name'] + ' ' + a['last_name']).lower()
    if k in staff_people:
        t = 'staff'
    else:
        t = 'attendee'
    groups[t]['attendees'].append(a)

for k,v in groups.items():
    print len(v['attendees']), k

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

def draw_info(image, first_name, last_name, caption, python_experience, logo, color_name, color_info):
    d = ImageDraw.Draw(image)

    max_width = BADGE['width'] - BADGE['first_name'][0] - 10
    if FONTS['name'].getsize(first_name.upper())[0] > max_width or FONTS['name'].getsize(last_name)[0] > max_width:
        font = FONTS['name_small']
    else:
        font = FONTS['name']

    def text(coord, text, font, color):
        x, y = coord
        for c in 0, 1:
            cx = x + c * BADGE['width']
            cy = y - font.getsize(text)[1]
            d.text((cx, cy), text, font = font, fill = color) 

    def multiline(coord, text, font, color):
        x, y = coord
        for c in 0, 1:
            cx = x + c * BADGE['width']
            cy = y - font.getsize(text)[1]
            lines = wrap_text(font, text, max_width)
            for l in lines:
                d.text((cx, cy), l, font = font, fill = color) 
                cy += font.getsize(l)[1] + 8

    text(BADGE['first_name'], first_name, font, color_name)
    text(BADGE['last_name'], last_name, FONTS['name_small'], color_name)

    if caption:
        multiline(BADGE['info'], caption, FONTS['info'], color_info)

    if logo and python_experience:
        w, h = logo.size
        spacer = int(2 * MM2INCH * DPI)
        x, y = BADGE['experience']
        y -= h
        for c in 0, 1:
            cx = x + c * BADGE['width']
            for _ in range(python_experience+1):
                image.paste(logo, (cx, y))
                cx += w +spacer

def assemble_page(images, cols=3, rows=3, marker=True):
    w0, h0 = images[0].size
    x0 = (PAGE_SIZE[0] - w0 * cols) / 2
    y0 = (PAGE_SIZE[1] - h0 * rows) / 2

    page = Image.new('RGB', PAGE_SIZE, (255, 255, 255))
    for ix, i in enumerate(images):
        col = ix % cols
        row = ix / rows
        x = x0 + col * w0
        y = y0 + row * h0
        page.paste(i, (x, y))

    if marker and BADGE['abbondanza']:
        draw = ImageDraw.Draw(page)
        a = BADGE['abbondanza']
        line_width = int(0.5 * MM2INCH * DPI)
        def m(p0, p1):
            p0 = tuple(map(int, p0))
            p1 = tuple(map(int, p1))
            draw.line((p0, p1), fill = (0, 0, 0), width = line_width)
        for ix, i in enumerate(images):
            col = ix % cols
            row = ix / rows
            x1 = x0 + col * w0
            y1 = y0 + row * h0
            x2 = x1 + w0
            y2 = y1 + h0

            m((x1+a, y1), (x1+a, y1+a/2))
            m((x1, y1+a), (x1+a/2, y1+a))

            m((x2-a, y1), (x2-a, y1+a/2))
            m((x2, y1+a), (x2-a/2, y1+a))

            m((x2, y2-a), (x2-a/2, y2-a))
            m((x2-a, y2), (x2-a, y2-a/2))

            m((x1, y2-a), (x1+a/2, y2-a))
            m((x1+a, y2), (x1+a, y2-a/2))
    return page

for t, data in groups.items():
    image = data['image']
    attendees = data['attendees']
    pages = len(attendees) / BADGE_PER_PAGE + 1
    print '%s:' % t, pages, 'pages'
    color = colors.get(t, colors[None])
    count = 1
    for block in grouper(BADGE_PER_PAGE, sorted(attendees, key = lambda x: x['last_name'].strip())):
        print '\t page', count
        images = []
        for ix, a in enumerate(block):
            i = image.copy()
            if a is None:
                first_name = last_name = caption = ''
                python_experience = 0
                logo = None
            else:
                first_name = a['first_name'].upper().strip()
                last_name = string.capwords(a['last_name'].strip())
                if a['badge_caption'] and a['badge_caption'].lower() not in ('sig', 'sig.', 'ing', 'ing.', 'mr', 'mr.', 'mrs', 'mrs.', 'dr.', 'dr'):
                    caption = a['badge_caption'].strip()
                else:
                    caption = None
                python_experience = a['python_experience']
                logo = LOGO.get(('%s %s' % (first_name, last_name)).lower(), LOGO.get(None))
                print '\t\t', first_name, last_name
            draw_info(i, first_name, last_name, caption, python_experience, logo, color['name'], color['info'])
            if RESIZE:
                i = i.resize(map(lambda x: int(x*RESIZE), i.size), Image.ANTIALIAS)
            images.append(i)

        if images:
            name = 'output/[%s] pag %s-%s.tif' % (t, str(count).zfill(2), str(pages).zfill(2))
            page = assemble_page(images)
            page.save(name, dpi=(DPI, DPI))

        count += 1

    abbondanza = int(math.ceil(pages * 0.15))
    print 'abbondanza', abbondanza
    for ix in range(abbondanza):
        name = 'output/[%s][vuoti] pag %s-%s.tif' % (t, str(ix+1).zfill(2), str(abbondanza).zfill(2))
        page = assemble_page([image.copy()] * BADGE_PER_PAGE)
        page.save(name, dpi=(DPI, DPI))

