# -*- coding: UTF-8 -*-
import Image, ImageFont
import os.path

_FONT_NAME = 'Arial_Unicode.ttf'
_FONTS = {
    'name': ImageFont.truetype(_FONT_NAME, 16 * 8),
    'name_small': ImageFont.truetype(_FONT_NAME, 10 * 8),
    'info': ImageFont.truetype(_FONT_NAME, 8 * 8),
}
images = 'allyourbase.png apple.png bertos.png bofh.png bycicle.png cake.png camcorder.png campi.png challenge.png ciuccio.png disqus.png dontpanic.png enthought.png fedora.png fluidinfo.png f-secure.png giullare.png iphone.png lundh.png male.png maya.png merengue.png moinmoin.png openquake.png openstack.png panino.png perl.png plaster.png postgres.png pycharm.png pyhp.png pypy.png pyside.png rapple.png riverbank.png royale.png skeleton.png sourceforge.png spiderman.png spotify.png stackless.png taz.png ubuntu.png wizard.png'
_ICONS = {
    None: Image.open('logo.png').convert('RGBA').resize((64, 64)),
}

for _ in images.split(' '):
    _ICONS[os.path.splitext(_)[0]] = Image.open('jokes/' + _).convert('RGBA').resize((64, 64))

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
    name_width = max(_FONTS['name'].getsize(first_name)[0], _FONTS['name'].getsize(last_name)[0])
    if name_width > w - 60:
        font = _FONTS['name_small']
        name_y = 400, 510
    else:
        font = _FONTS['name']
        name_y = 460, 590
    
    lname = ticket['name'].lower()
    ltag = tagline.lower()
    if lname == 'lorenzo berni':
        logo = _ICONS['rapple']
    elif lname == 'paolo romolini':
        logo = _ICONS['campi']
    elif lname == 'francesco pallanti':
        logo = _ICONS['cake']
    elif lname == 'lorenzo mancini':
        logo = _ICONS['male']
    elif lname == 'giovanni bajo':
        logo = _ICONS['skeleton']
    elif lname == 'dario trovato':
        logo = _ICONS['camcorder']
        ticket['experience'] = 5
    elif lname == 'simone federici':
        logo = _ICONS['plaster']
    elif lname in ('didrik pinte', 'damian campbell'):
        logo = _ICONS['enthought']
    elif lname in ('matti airas', 'thomas perl'):
        logo = _ICONS['pyside']
    elif lname == 'caroline tice':
        logo = _ICONS['apple']
    elif lname == 'phil thompson':
        logo = _ICONS['riverbank']
    elif lname in ('armin rigo', 'antonio cuni', 'laura creighton', 'jacob hallén'):
        logo = _ICONS['pypy']
    elif lname == 'valentino volonghi':
        logo = _ICONS['giullare']
    elif lname == 'christian tismer':
        logo = _ICONS['stackless']
    elif lname in ('fabio rotondo', 'andrea rotondo', 'giulio porta', 'davide davin'):
        logo = _ICONS['pyhp']
    elif lname in ('pär von zweigbergk', 'jon åslund', 'nick barkas'):
        logo = _ICONS['spotify']
    elif lname == 'fredrik lundh':
        logo = _ICONS['lundh']
    elif lname == 'taz':
        logo = _ICONS['taz']
    elif lname in ('santtu jarvi', 'hannu maaranen', 'mathias fröjdman'):
        logo = _ICONS['f-secure']
    elif lname == 'nicola \'woody\' ferruzzi':
        logo = _ICONS['iphone']
    elif lname in ('nicola larosa', 'paolo sammicheli', 'andrea corbellini'):
        logo = _ICONS['ubuntu']
    elif lname == 'david cramer':
        logo = _ICONS['disqus']
    elif lname == 'reimar bauer':
        logo = _ICONS['moinmoin']
    elif lname == 'nikola kudus':
        logo = _ICONS['maya']
    elif lname == 'gianluca sforna':
        logo = _ICONS['fedora']
    elif lname == 'tomaž šolc':
        logo = _ICONS['perl']
    elif lname == 'sten spans':
        logo = _ICONS['dontpanic']
    elif lname == 'gianni moschini':
        logo = _ICONS['allyourbase']
    elif lname in ('andrea cerisara', 'marco milanesi', 'lars butler', 'john tarter'):
        logo = _ICONS['openquake']
    elif lname in ('esteve fernandez', 'nicholas tollervey'):
        logo = _ICONS['fluidinfo']
    elif lname == 'manuel saelices':
        logo = _ICONS['merengue']
    elif lname == 'harry percival':
        logo = _ICONS['panino']
    elif lname == 'morten brekkevold':
        logo = _ICONS['bycicle']
    elif lname == 'andreas dreier':
        logo = _ICONS['royale']
    elif lname == 'robin harrison':
        logo = _ICONS['spiderman']
    elif lname == 'thierry carrez':
        logo = _ICONS['openstack']
    elif lname == 'mark ramm':
        logo = _ICONS['sourceforge']
    elif lname == 'francesco sacchi':
        logo = _ICONS['bertos']
    elif lname == 'andrey vlasovskikh':
        logo = _ICONS['pycharm']
    elif lname in ('stefano fedrigo', 'simone roselli'):
        logo = _ICONS['bofh']
    elif 'drop table' in ltag:
        logo = _ICONS['ciuccio']
    elif 'challenge accepted' in ltag:
        logo = _ICONS['challenge']
    elif 'postgresql' in ltag:
        logo = _ICONS['postgres']
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
