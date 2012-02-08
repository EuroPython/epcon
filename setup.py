#!/usr/bin/env python

from distutils.core import setup

import os
import os.path

def recurse(path):
    B = 'conference'
    output = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(B, path)):
        for d in filter(lambda x: x[0] == '.', dirnames):
            dirnames.remove(d)
        for f in filenames:
            output.append(os.path.join(dirpath, f)[len(B)+1:])
    return output

setup(name='conference',
    version='0.1',
    description='django conference',
    author='dvd',
    author_email='dvd@develer.com',
    packages=[
        'conference',
        'conference.management',
        'conference.management.commands',
        'conference.migrations',
        'conference.templatetags',
        'conference.utils',
    ],
    package_data={
        'conference': sum(map(recurse, ('deps', 'locale', 'static', 'templates')), []),
    },
    install_requires=[
        'httplib2',
        'fancy_tag',
    ],
)
