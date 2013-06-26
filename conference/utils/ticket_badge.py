#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import json
import math
import optparse
import os
import os.path
import re
import sys
from PIL import Image, ImageDraw
from itertools import izip_longest

parser = optparse.OptionParser(usage='%(prog)s [options] output_dir')
parser.add_option("-i", "--input",
                    dest="input",
                    default=None,
                    action="store",
                    help="input file (default stdin)")
parser.add_option("-p", "--page-size",
                    dest="page_size",
                    default="490x318",
                    action="store",
                    help="page size (mm)")
parser.add_option("-d", "--dpi",
                    dest="dpi",
                    default=300,
                    action="store",
                    type="int",
                    help="dpi")
parser.add_option("-r", "--resize",
                    dest="resize",
                    default=None,
                    action="store",
                    type="float",
                    help="resize factor (if any)")
parser.add_option("-n", "--per-page",
                    dest="per_page",
                    default=9,
                    action="store",
                    type="int",
                    help="badge per page")
parser.add_option("-m", "--no-marker",
                    dest="no_marker",
                    default=False,
                    action="store_true",
                    help="don't draw the crop marks")
parser.add_option("-c", "--conf",
                    dest="conf",
                    default="conf.py",
                    action="store",
                    help="configuration script")
parser.add_option("-e", "--empty-pages",
                    dest="empty_pages",
                    default="0",
                    action="store",
                    help="prepare x empty pages")

opts, args = parser.parse_args()

try:
    output_dir = args[0]
except IndexError:
    parser.print_usage()

conf = {}
os.chdir(os.path.dirname(opts.conf))
execfile(os.path.basename(opts.conf), conf)

MM2INCH = 0.03937
tickets = conf['tickets']
ticket = conf['ticket']
DPI = opts.dpi
WASTE = conf.get('WASTE', 0) * MM2INCH * DPI
PAGE_MARGIN = int(conf.get('PAGE_MARGIN', 10) * MM2INCH * DPI)

if opts.page_size == 'A3':
    psize = "420x297"
elif opts.page_size == 'A4':
    psize = "297x210"
else:
    psize = opts.page_size
PAGE_SIZE = map(lambda x: int(int(x) * MM2INCH * DPI), psize.split('x'))

data = json.loads(sys.stdin.read())

groups = tickets(data)

def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)

def wrap_text(font, text, width):
    words = re.split(' ', text)
    lines = []
    while words:
        word = words.pop(0).strip()
        if not word:
            continue
        if not lines:
            lines.append(word)
        else:
            line = lines[-1]
            w, h = font.getsize(line + ' ' + word)
            if w <= width:
                lines[-1] += ' ' + word
            else:
                lines.append(word)

    for ix, line in enumerate(lines):
        line = line.strip()
        while True:
            w, h = font.getsize(line)
            if w <= width:
                break
            line = line[:-1]
        lines[ix] = line
    return lines

def draw_info(image, max_width, text, pos, font, color, line_offset=8):
    d = ImageDraw.Draw(image)

    cx = pos[0]
    cy = pos[1] - font.getsize(text)[1]
    lines = wrap_text(font, text, max_width)
    for l in lines:
        d.text((cx, cy), l, font = font, fill = color)
        cy += font.getsize(l)[1] + line_offset

def assemble_page(images):
    #cols = rows = int(math.ceil(math.sqrt(len(images))))
    #w0, h0 = images[0].size
    #x0 = (PAGE_SIZE[0] - w0 * cols) / 2
    #y0 = (PAGE_SIZE[1] - h0 * rows) / 2

    page = Image.new('RGBA', PAGE_SIZE, (255, 255, 255, 255))
    x = y = PAGE_MARGIN
    limits = PAGE_SIZE[0] - 2*PAGE_MARGIN, PAGE_SIZE[1] - 2*PAGE_MARGIN
    for img in images:
        size = img.size
        if x + size[0] > limits[0]:
            x = PAGE_MARGIN
            y += size[1]
        elif y + size[1] > limits[1]:
            y += size[1]
        page.paste(img, (x, y), img)
        x += size[0]
    return page

#    TODO: reimplementare la gestione dei segni di taglio
#    if not opts.no_marker and WASTE:
#        draw = ImageDraw.Draw(page)
#        a = WASTE
#        line_width = int(0.5 * MM2INCH * DPI)
#        def m(p0, p1):
#            p0 = tuple(map(int, p0))
#            p1 = tuple(map(int, p1))
#            draw.line((p0, p1), fill = (0, 0, 0), width = line_width)
#        for ix, i in enumerate(images):
#            col = ix % cols
#            row = ix / rows
#            x1 = x0 + col * w0
#            y1 = y0 + row * h0
#            x2 = x1 + w0
#            y2 = y1 + h0
#
#            m((x1+a, y1), (x1+a, y1+a/2))
#            m((x1, y1+a), (x1+a/2, y1+a))
#
#            m((x2-a, y1), (x2-a, y1+a/2))
#            m((x2, y1+a), (x2-a/2, y1+a))
#
#            m((x2, y2-a), (x2-a/2, y2-a))
#            m((x2-a, y2), (x2-a, y2-a/2))
#
#            m((x1, y2-a), (x1+a/2, y2-a))
#            m((x1+a, y2), (x1+a, y2-a/2))
#    return page

def add_page(name, page):
    with file(os.path.join(output_dir, name), 'w') as out:
        page.save(out, 'TIFF', dpi=(DPI, DPI))

def render_badge(image, attendee, utils, resize_factor=None):
    i = ticket(image, attendee, utils=utils)
    if resize_factor:
        nsize = i.size[0] * resize_factor, i.size[1] * resize_factor
        i = i.resize(nsize, Image.ANTIALIAS)
    return i

for group_type, data in sorted(groups.items()):
    image = data['image']
    attendees = data['attendees']
    pages = len(attendees) / opts.per_page
    if len(attendees) % opts.per_page:
        pages += 1

    utils = {
        'wrap_text': wrap_text,
        'draw_info': draw_info,
    }
    count = 1
    for block in grouper(opts.per_page, attendees):
        if block:
            images = []
            for a in block:
                badge = render_badge(image, a, utils=utils, resize_factor=opts.resize)
                images.append(badge)
            page = assemble_page(images)

            name = '[%s] pag %s-%s.tif' % (group_type, str(count).zfill(2), str(pages).zfill(2))
            print >>sys.stderr, name
            add_page(name, page)

        count += 1

    if opts.empty_pages.endswith('%'):
        additional = int(math.ceil(pages * float(opts.empty_pages[:-1]) / 100 ))
    else:
        additional = int(opts.empty_pages)
    for ix in range(additional):
        name = '[%s][vuoti] pag %s-%s.tif' % (group_type, str(ix+1).zfill(2), str(additional).zfill(2))
        images = [ render_badge(image, None, utils=utils, resize_factor=opts.resize) for x in range(opts.per_page) ]
        add_page(name, assemble_page(images))
