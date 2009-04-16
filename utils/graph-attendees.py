#!/usr/bin/env python
# -*- coding: UTF-8 -*-

URL = 'http://assopy.pycon.it/conference/getinfo.py/geo_sold'

import urllib2
import simplejson
from datetime import datetime, date, time, timedelta
from collections import defaultdict

attendees = simplejson.loads(urllib2.urlopen(URL).read())

data = defaultdict(lambda: 0)
for entry in attendees:
    m, d, y = map(int, entry['data_acquisto'].split('/'))
    w = date(y, m, d)
    data[w] += entry['numero_biglietti']


print 'attendees:', sum(data.values())
from pygooglechart import XYLineChart, Axis

rows = sorted(data.items())
start = rows[0][0]
end = rows[-1][0]

deadlines = {
    date(2009, 4, 13): None,
}

d = start
pos = 0
step = timedelta(days=1)
while d != end:
    if d in deadlines:
        deadlines[d] = pos
    d += step
    pos += 1
    if d not in data:
        data[d] = 0
rows = sorted(data.items())

title = str(sum(data.values())) + ' partecipanti al PyCon Tre - ' + start.strftime('%d %b %Y') + ' / ' + end.strftime('%d %b %Y')
chart = XYLineChart(
    width = 1000, height = 300,
    title = title, y_range = [0, 420]
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

axis = range(0, 420, 420 / 6)
axis[-1] = 420
chart.set_axis_labels(Axis.LEFT, map(str, axis))


axis = [ datetime.combine(start, time()) ]
step = (end - start) / 15
end = datetime.combine(end, time())
while axis[-1] < end:
    axis.append(axis[-1] + step)
axis[-1] = end

for ix, d in enumerate(axis):
    axis[ix] = d.strftime('%d %b')

chart.set_axis_labels(Axis.BOTTOM, axis)

for pos in deadlines.values():
    p = float(pos) / len(rows)
    chart.add_vertical_range('9966cc', p, p + 0.004)

chart.download('attendees.png')
