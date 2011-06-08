#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import json
import math
import optparse
import os
import os.path
import re
import sys
import tarfile
import time
import Image, ImageDraw
from cStringIO import StringIO
from itertools import izip_longest

parser = optparse.OptionParser()
parser.add_option("-i", "--input",
                    dest="input",
                    default=None,
                    action="store",
                    help="input file (default stdin)")
parser.add_option("-o", "--output",
                    dest="output",
                    default=None,
                    action="store",
                    help="output file (tar) (default stdout)")
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
                    default="15%",
                    action="store",
                    help="prepare x empty pages")

opts, args = parser.parse_args()

conf = {}
os.chdir(os.path.dirname(opts.conf))
execfile(os.path.basename(opts.conf), conf)

MM2INCH = 0.03937
tickets = conf['tickets']
ticket = conf['ticket']
DPI = opts.dpi
WASTE = conf.get('WASTE', 0) * MM2INCH * DPI
PAGE_SIZE = map(lambda x: int(int(x) * MM2INCH * DPI), opts.page_size.split('x'))

data = json.loads(sys.stdin.read())

groups = tickets(data)

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

def draw_info(image, max_width, text, pos, font, color):
    d = ImageDraw.Draw(image)

    #max_width = BADGE['width'] - BADGE['first_name'][0] - 10
    #if FONTS['name'].getsize(first_name.upper())[0] > max_width or FONTS['name'].getsize(last_name)[0] > max_width:
    #    font = FONTS['name_small']
    #else:
    #    font = FONTS['name']

    cx = pos[0]
    cy = pos[1] - font.getsize(text)[1]
    lines = wrap_text(font, text, max_width)
    for l in lines:
        d.text((cx, cy), l, font = font, fill = color) 
        cy += font.getsize(l)[1] + 8

def assemble_page(images):
    cols = rows = int(math.ceil(math.sqrt(len(images))))
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

    if not opts.no_marker and WASTE:
        draw = ImageDraw.Draw(page)
        a = WASTE
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

if opts.output is None:
    output = tarfile.open(fileobj=sys.stdout, mode='w:gz')
else:
    output = tarfile.open(opts.output, mode='w:gz')

def add_page(name, page):
    out = StringIO()
    page.save(out, 'TIFF', dpi=(DPI, DPI))
    tinfo = tarfile.TarInfo(name=name)
    tinfo.size = len(out.getvalue())
    tinfo.mtime = time.time()
    out.seek(0)
    output.addfile(tinfo, out)

for group_type, data in groups.items():
    image = data['image']
    attendees = data['attendees']
    pages = len(attendees) / opts.per_page + 1

    count = 1
    for block in grouper(opts.per_page, attendees):
        images = []
        for ix, a in enumerate(block):
            i = image.copy()
            if a is not None:
                texts = ticket(i, a)
                for t, pos, font, color in texts:
                    draw_info(i, data['max_width'], t, pos, font, color)
            if opts.resize:
                i = i.resize(map(lambda x: int(x*opts.resize), i.size), Image.ANTIALIAS)
            images.append(i)

        if images:
            name = '[%s] pag %s-%s.tif' % (group_type, str(count).zfill(2), str(pages).zfill(2))
            page = assemble_page(images)
            add_page(name, page)

        count += 1

    if opts.empty_pages.endswith('%'):
        additional = int(math.ceil(pages * float(opts.empty_pages[:-1]) / 100 ))
    else:
        additional = int(opts.empty_pages)
    for ix in range(additional):
        name = '[%s][vuoti] pag %s-%s.tif' % (group_type, str(ix+1).zfill(2), str(additional).zfill(2))
        page = assemble_page([image.copy()] * opts.per_page)
        add_page(name, page)

output.close()
