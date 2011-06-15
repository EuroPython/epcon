import Image, ImageFont

_FONT_NAME = 'Arial_Unicode.ttf'
_FONTS = {
    'name': ImageFont.truetype(_FONT_NAME, 16 * 8),
    'name_small': ImageFont.truetype(_FONT_NAME, 10 * 8),
    'info': ImageFont.truetype(_FONT_NAME, 8 * 8),
}
_ICONS = {
    None: Image.open('logo.png').convert('RGBA').resize((64, 64)),
    'apple': Image.open('apple.png').convert('RGBA').resize((64, 64)),
    'ciuccio': Image.open('ciuccio.png').convert('RGBA').resize((64, 64)),
}

WASTE = 3

def tickets(tickets):
    groups = {
        'staff': {
            'image': Image.open('staff.png').convert('RGBA'),
            'max_width': 0,
            'attendees': [],
        },
        'lite': {
            'image': Image.open('lite.png').convert('RGBA'),
            'max_width': 0,
            'attendees': [],
        },
        'standard': {
            'image': Image.open('standard.png').convert('RGBA'),
            'max_width': 0,
            'attendees': [],
        },
        'day1': {
            'image': Image.open('day1.png').convert('RGBA'),
            'max_width': 0,
            'attendees': [],
        },
        'day2': {
            'image': Image.open('day2.png').convert('RGBA'),
            'max_width': 0,
            'attendees': [],
        },
        'day3': {
            'image': Image.open('day3.png').convert('RGBA'),
            'max_width': 0,
            'attendees': [],
        },
        'day4': {
            'image': Image.open('day4.png').convert('RGBA'),
            'max_width': 0,
            'attendees': [],
        },
        'day5': {
            'image': Image.open('day5.png').convert('RGBA'),
            'max_width': 0,
            'attendees': [],
        },
    }
    for t in tickets:
        if t.get('staff'):
            g = 'staff'
        else:
            if t['fare']['code'][2] == 'D':
                g = 'day' + t['days'].split(',')[0]
                if g not in groups:
                    g = 'day1'
            elif t['fare']['code'][2] == 'F':
                g = 'standard'
            elif t['fare']['code'][2] == 'S':
                g = 'lite'
        groups[g]['attendees'].append(t)
    
    for v in groups.values():
        v['max_width'] = v['image'].size[0] / 2 - 60
        v['attendees'].sort(key=lambda x: x['name'])
    return groups

def ticket(image, ticket):
    import string
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
    name_width = max(_FONTS['name'].getsize(first_name)[0], _FONTS['name'].getsize(last_name)[0])
    if name_width > w - 60:
        font = _FONTS['name_small']
        name_y = 400, 510
    else:
        font = _FONTS['name']
        name_y = 460, 590
    
    check = tagline.lower()
    if 'drop table' in tagline.lower():
        logo = _ICONS['ciuccio']
    elif ticket['name'].lower() == 'lorenzo berni':
        logo = _ICONS['apple']
    else:
        logo = _ICONS[None]
    output = [
        (first_name, (50, name_y[0]), font, color_name),
        (last_name, (50, name_y[1]), font, color_name),
        (tagline, (50, 880), _FONTS['info'], color_info),
    ] + [
        (logo, (50 + (logo.size[0] + 20) * ix, 700)) for ix in range(ticket.get('experience', 0))
    ]
    mirrored = [
        (row[0], ) + ((w + row[1][0], row[1][1]),) + row[2:]
        for row in output
    ]
    return output + mirrored
