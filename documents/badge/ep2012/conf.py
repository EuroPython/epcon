# -*- coding: UTF-8 -*-
from PIL import Image, ImageFont
from PyQRNative import QRCode, QRErrorCorrectLevel

_FONT_NAME = 'Arial_Unicode.ttf'
_FONTS = {
    'name': ImageFont.truetype(_FONT_NAME, 16 * 8),
    'name_small': ImageFont.truetype(_FONT_NAME, 10 * 8),
    'info': ImageFont.truetype(_FONT_NAME, 8 * 8),
}
PY_LOGO = Image.open('logo.png').convert('RGBA').resize((64, 64))

def tickets(tickets):
    groups = {}
    for k in ('staff', 'lite', 'standard', 'day1', 'day2', 'day3', 'day4', 'day5'):
        groups[k] = {
            'image': Image.open(k + '.png').convert('RGBA'),
            'attendees': [],
        }
    for t in tickets:
        if t.get('staff'):
            g = 'staff'
        else:
            if t['fare']['code'][2] == 'D':
                g = 'day' + t['days'].split(',')[0]
                if g not in groups:
                    g = 'day1'
            elif t['fare']['code'][2] == 'S':
                g = 'standard'
            elif t['fare']['code'][2] == 'L':
                g = 'lite'
            else:
                1/0
        groups[g]['attendees'].append(t)

    for v in groups.values():
        v['attendees'].sort(key=lambda x: x['name'])
    return groups

def ticket(image, ticket, utils):
    image = image.copy()
    if not ticket:
        return image

    import string
    _multi = (
        'pier maria', 'gian battista', 'arnaldo miguel', 'dr. yves', 'dr. stefan', 'mr yun',
    )
    check = ticket['name'].lower()
    for x in _multi:
        if check.startswith(x):
            first_name = ticket['name'][:len(x)].strip()
            last_name = ticket['name'][len(x):].strip()
            break
    else:
        try:
            first_name, last_name = ticket['name'].split(' ', 1)
        except ValueError:
            first_name = ticket['name']
            last_name = ''
    tagline = ticket.get('tagline', '').strip()

    first_name = first_name.upper().strip()
    last_name = string.capwords(last_name.strip())

    color_name = 75, 129, 135
    color_info = 125, 111, 96

    w = image.size[0] / 2
    name_width = max(
        _FONTS['name'].getsize(first_name)[0],
        _FONTS['name'].getsize(last_name)[0])
    if name_width > w - 60:
        font = _FONTS['name_small']
        name_y = 400, 510
    else:
        font = _FONTS['name']
        name_y = 460, 590

    if ticket['badge_image']:
        logo = Image.open(ticket['badge_image']).convert('RGBA').resize((64, 64))
    else:
        logo = PY_LOGO
    rows = [
        (first_name, (50, name_y[0]), font, color_name),
        (last_name, (50, name_y[1]), font, color_name),
        (tagline, (50, 880), _FONTS['info'], color_info),
    ] + [
        (logo, (50 + (logo.size[0] + 20) * ix, 700)) for ix in range(ticket.get('experience', 0))
    ]
    mirrored = [
        (row[0], ) + ((w + row[1][0], row[1][1]),) + row[2:]
        for row in rows
    ]
    for row in rows + mirrored:
        if isinstance(row[0], Image.Image):
            image.paste(row[0], row[1], row[0])
        else:
            t, pos, font, color  = row
            utils['draw_info'](image, w - 60, t, pos, font, color)

    if ticket.get('profile-link'):
        qr = QRCode(8, QRErrorCorrectLevel.H)
        qr.addData(ticket['profile-link'])
        qr.make()
        im = qr.makeImage().resize((int(12*0.03937*300), int(12*0.03937*300)))
        image.paste(im, (689, 1070))
    return image
