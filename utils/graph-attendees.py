#!/usr/bin/env python
# -*- coding: UTF-8 -*-

URL = 'http://assopy.pycon.it/conference/getinfo.py/geo_sold'

import urllib2
import simplejson
import datetime
from collections import defaultdict

attendees = simplejson.loads(urllib2.urlopen(URL).read())

data = defaultdict(lambda: 0)
for entry in attendees:
    m, d, y = map(int, entry['data_acquisto'].split('/'))
    w = datetime.date(y, m, d)
    data[w] += entry['numero_biglietti']


print 'attendees:', sum(data.values())
from pygooglechart import XYLineChart, Axis

rows = sorted(data.items())
start = rows[0][0]
end = rows[-1][0]

title = 'Partecipanti al PyCon Tre - ' + start.strftime('%d %b %Y') + ' / ' + end.strftime('%d %b %Y')
chart = XYLineChart(
    width = 1000, height = 300,
    title = title,
)
x_values = range(len(rows))

chart.add_data(x_values)
row = []
total = 0
for d, count in rows:
    total += count
    row.append(total)
chart.add_data(row)

chart.add_data(x_values)
chart.add_data([ x[1] for x in rows ])

chart.add_data(x_values)
chart.add_data([ 0 ] * len(x_values))

chart.set_colours(['000000', 'ff0000', '000000'])
chart.add_fill_range('99ccff', 0, 2)

axis = range(0, total, total /6)
axis[-1] = total
chart.set_axis_labels(Axis.LEFT, map(str, axis))


axis = [ start ]
step = (end - start) / 15
for _ in range(14):
    axis.append(axis[-1] + step)
axis[-1] = end

for ix, d in enumerate(axis):
    axis[ix] = d.strftime('%d %b')

chart.set_axis_labels(Axis.BOTTOM, axis)

chart.download('x.png')
