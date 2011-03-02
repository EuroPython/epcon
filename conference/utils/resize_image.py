#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import ConfigParser
import fnmatch
import logging
import os
import os.path
import sys
from optparse import OptionParser

from PIL import Image

parser = OptionParser(usage = '%prog [-v] [-a] [-x glob] [-n] [work_dir]')
parser.add_option('-v', '--verbose',
    dest = 'verbose', action = 'store_true', default = False)
parser.add_option('-n', '--dry-run',
    dest = 'dry_run', action = 'store_true', default = False)
parser.add_option('-x', '--exclude',
    dest = 'exclude', action = 'store', default = None)
parser.add_option('-a', '--all',
    dest = 'all', action = 'store_true', default = False,
    help = 'processa tutte le immagini, non solo quelle modificate')

(options, args) = parser.parse_args()
if len(args) > 1:
    parser.error("incorrect number of arguments")
else:
    try:
        work_dir = args[0]
    except IndexError:
        work_dir = '.'

logging.basicConfig()
log = logging.getLogger('p3')
if options.verbose:
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.WARNING)

def inspect():
    for root, subdirs, files in os.walk(work_dir):
        for f in files:
            if f.endswith('.ini'):
                yield os.path.join(root, f)

def parseConfigFile(fpath):
    parser = ConfigParser.SafeConfigParser()
    good = parser.read(fpath)
    if not good:
        raise ValueError('invalid file')
    try:
        output = parser.get('resize', 'output')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        log.warn('output value not found, fallbak to "resized"')
        output = 'resized'
    try:
        rule = parser.get('resize', 'rule')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        raise ValueError('value resize/rule not found')
    actions = [ r.split('=', 1) for r in rule.split(';') ]
    out = []
    for a in actions:
        if len(a) > 1:
            out.append((a[0], a[1].split(',')))
        else:
            out.append((a[0], tuple()))
    return output, out

class Resize(object):
    def __init__(self, cfg):
        self.cfg = cfg

    def __call__(self, src, dst):
        img = Image.open(src)
        if img.mode not in ('RGBA', ):
            img = img.convert('RGBA')
        for action, params in self.cfg:
            try:
                img = getattr(self, action)(img, *params)
            except AttributeError, e:
                raise ValueError('invalid action: %s' % action)
            except TypeError, e:
                raise ValueError('invalid params for action: %s' % action)
        if not options.dry_run:
            img.save(dst, 'JPEG', quality=90)

    def alphacolor(self, img):
        """
        Se l'immagine non ha già un canale alpha valido ne crea uno rendendo
        trasparente il colore del pixel in alto a sinistra.
        """
        band = img.split()[-1]
        colors = set(band.getdata())
        if len(colors) > 1:
            return img
        color = img.getpixel((0, 0))
        data = []
        TRANSPARENT = 0
        OPAQUE = 255
        for i in img.getdata():
            if i == color:
                data.append(TRANSPARENT)
            else:
                data.append(OPAQUE)
        img = img.copy()
        band.putdata(data)
        img.putalpha(band)
        return img

    def blend(self, img, perc):
        """
        rende l'immagine trasparente
        """
        perc = float(perc)
        if perc == 1:
            # completamente opaca
            return img
        band = img.split()[-1]
        data = [ int(i * perc) for i in band.getdata() ]
        img = img.copy()
        band.putdata(data)
        img.putalpha(band)
        return img

    def box(self, img, size):
        """
        ridimensiona in maniera proporzionale
        """
        size = map(float, size.split('x'))
        iw, ih = img.size
        rw = iw / size[0]
        rh = ih / size[1]
        if rw > rh:
            nw = size[0]
            nh = ih * nw / iw
        else:
            nh = size[1]
            nw = iw * nh / ih
        return img.resize((int(nw), int(nh)), Image.ANTIALIAS)

    def canvas(self, img, size, bg):
        """
        crea una nuova canvas con il color passato e ci incolla sopra (centrata
        l'immagine passata)
        """
        size = map(int, size.split('x'))
        if size[0] == -1:
            size[0] = img.size[0]
        if size[1] == -1:
            size[1] = img.size[1]
        i = Image.new('RGBA', size, bg)
        paste_point = []
        for d1, d2 in zip(size, img.size):
            if d1 < d2:
                paste_point.append(0)
            else:
                paste_point.append((d1 - d2) / 2)
        if img.mode == 'RGBA':
            i.paste(img, tuple(paste_point), img)
        else:
            i.paste(img, tuple(paste_point))
        return i

    def reduce_canvas(self, img, size):
        nw, nh = map(int, size.split('x'))
        w, h = img.size

        if nw < w or nh < h:
            i = self.canvas(img, size, '#ffffff')
        else:
            i = img
        return i

def resize_dir(cfg, src, dst):
    def f(fname):
        if fname.endswith('.ini') or fname.startswith('.'):
            return False
        if options.exclude:
            return not fnmatch.fnmatch(fname, options.exclude)
        else:
            return True
        
    count = 0
    resizer = Resize(cfg)
    for fname in filter(f, os.listdir(src)):
        spath = os.path.join(src, fname)
        if not os.path.isfile(spath):
            continue
        dpath = os.path.join(dst, os.path.splitext(fname)[0] + '.jpg')
        if not options.all:
            if os.path.isfile(dpath):
                sstat = os.stat(spath)
                dstat = os.stat(dpath)
                if dstat.st_mtime > sstat.st_mtime:
                    continue
        log.info('resizing %s', spath)
        try:
            resizer(spath, dpath)
        except IOError:
            log.info('invalid image: %s', spath)
            continue
        count += 1
    return count

if options.dry_run:
    log.info('dry run mode, nothing will be actually written to disk')
log.info('inspecting %s', work_dir)
for cpath in inspect():
    log.info('config file found: %s', cpath)
    try:
        output, cfg = parseConfigFile(cpath)
    except ValueError, e:
        log.warn('skipping config file: %s', e)
        continue
    src_dir = os.path.dirname(cpath)
    dst_dir = os.path.join(src_dir, output)
    if not os.path.isdir(dst_dir):
        log.info('mkdirs %s', dst_dir)
        if not options.dry_run:
            os.makedirs(dst_dir)
    try:
        count = resize_dir(cfg, src_dir, dst_dir)
    except ValueError, e:
        log.warn('aborting: %s', e)
        sys.exit(1)
    log.info('resized %d files', count)
