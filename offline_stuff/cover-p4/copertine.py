#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import re
import urllib2
import Image, ImageFont, ImageDraw
from lxml import etree

URL = 'http://www.pycon.it/conference/pycon4/talks.xml'

FONTS = {
    'titolo': ImageFont.truetype('League Gothic.otf', 36),
    'autore': ImageFont.truetype('Georgia_Bold.ttf', 21),
    'preposizioni': ImageFont.truetype('Georgia_Italic.ttf', 21),
}
IMAGE = Image.open('start.png')

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

def multiline(coord, text, font, color):
    x, y = coord
    max_width = IMAGE.size[0] - x * 2
    lines = wrap_text(font, text, max_width)
    twidth = 0
    for l in lines:
        d.text((x, y), l, font = font, fill = color) 
        fw, fh = font.getsize(l)
        y +=  fh + 8
        twidth = max(twidth, fw)
    return twidth

tree = etree.parse(urllib2.urlopen(URL))
for talk in tree.getroot().findall('talk'):
    title = talk.find('title').text
    autore = ', '.join([ a.get('name') for a in talk.findall('speaker') ])
    print title, '-', autore

    i = IMAGE.copy()
    d = ImageDraw.Draw(i)

    multiline((37, 144), title, font=FONTS['titolo'], color=(0x96, 0x11, 0x42))
    tw = multiline((37, 295), 'di', font=FONTS['preposizioni'], color=(0x4c, 0x5e, 0x5e))
    multiline((37 + tw + 8, 295), ' ' + autore, font=FONTS['autore'], color=(0x4c, 0x5e, 0x5e))

    fname = title.encode('ascii', 'ignore').replace(' ', '-').lower()
    i.save('output/%s.png' % fname)

