# -*- coding: UTF-8 -*-
from PIL import Image, ImageFont

_FONT_INFO = 'Arial_Unicode.ttf'
_FONT_NAME = 'League_Gothic.otf'
_FONTS = {
    'name': ImageFont.truetype(_FONT_NAME, 20 * 8),
    'name_small': ImageFont.truetype(_FONT_NAME, 15 * 8),
    'info': ImageFont.truetype(_FONT_INFO, 6 * 8),
}
PY_LOGO = {
    'staff': Image.open('logo-blu.png').convert('RGBA').resize((64, 64)),
    'all': Image.open('logo-panna.png').convert('RGBA').resize((64, 64)),
}

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
        v['attendees'].sort(key=lambda x: x['name'].lower())
    return groups


# http://stackoverflow.com/questions/765736/using-pil-to-make-all-white-pixels-transparent#answer-4531395
def distance2(a, b):
    return (a[0] - b[0]) * (a[0] - b[0]) + (a[1] - b[1]) * (a[1] - b[1]) + (a[2] - b[2]) * (a[2] - b[2])

def makeColorTransparent(image, color, thresh2=0):
    from PIL import ImageMath
    image = image.convert("RGBA")
    red, green, blue, alpha = image.split()
    image.putalpha(ImageMath.eval("""convert(((((t - d(c, (r, g, b))) >> 31) + 1) ^ 1) * a, 'L')""",
        t=thresh2, d=distance2, c=color, r=red, g=green, b=blue, a=alpha))
    return image

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
        parts = ticket['name'].split(' ')
        if len(parts) == 4 and parts[2].lower() not in ('de', 'van'):
            first_name = ' '.join(parts[:2])
            last_name =  ' '.join(parts[2:])
        else:
            first_name = parts[0]
            last_name = ' '.join(parts[1:])
    tagline = ticket.get('tagline', '').strip()

    first_name = first_name.upper().strip()
    last_name = string.capwords(last_name.strip())
    # irish and scotch
    last_name = last_name.replace('Mcc', 'McC')

    color_name = 74, 57, 50
    color_info = 74, 57, 50

    w = image.size[0] / 2
    name_width = max(
        _FONTS['name'].getsize(first_name)[0],
        _FONTS['name'].getsize(last_name)[0])
    if name_width > w - 87:
        font = _FONTS['name_small']
        name_y = 400, 510
    else:
        font = _FONTS['name']
        name_y = 490, 650

    if ticket['badge_image']:
        logo = Image.open(ticket['badge_image'])
        if logo.mode != 'RGBA':
            if logo.mode == 'LA':
                logo = logo.convert('RGBA')
            else:
                if logo.mode != 'RGB':
                    logo = logo.convert('RGB')
                logo = makeColorTransparent(logo, logo.getpixel((0, 0)), thresh2=150)
        logo = logo.resize((100, 100), Image.ANTIALIAS)
    else:
        if ticket.get('staff'):
            logo = PY_LOGO['staff']
        else:
            logo = PY_LOGO['all']
    rows = [
        (first_name, (87, name_y[0]), font, color_name),
        (last_name, (87, name_y[1]), font, color_name),
        (tagline, (87, 730), _FONTS['info'], color_info),
    ] + [
        (logo, (87 + (logo.size[0] + 20) * ix, 887)) for ix in range(ticket.get('experience', 0))
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

    return image
