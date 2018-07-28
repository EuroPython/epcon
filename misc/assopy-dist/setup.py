#!/usr/bin/env python

from distutils.core import setup

import os
import os.path

def recurse(path):
    B = 'assopy'
    output = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(B, path)):
        for d in [x for x in dirnames if x[0] == '.']:
            dirnames.remove(d)
        for f in filenames:
            output.append(os.path.join(dirpath, f)[len(B)+1:])
    return output

setup(name='assopy',
    version='0.1',
    description='django assopy',
    author='dvd',
    author_email='dvd@develer.com',
    packages=[
        'assopy',
        'assopy.clients',
        'assopy.management',
        'assopy.management.commands',
        'assopy.migrations',
        'assopy.templatetags',
        'assopy.stripe',
    ],
    package_data={
        'assopy': sum(list(map(recurse, ('deps', 'locale', 'static', 'templates', 'fixtures'))), []),
    },
    install_requires=[
        'suds',
        'stripe==1.19.1',
    ],
)
