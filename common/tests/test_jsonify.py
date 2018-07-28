import unittest
import datetime

import simplejson

from common.jsonify import json_dumps


class MyEncodeTestCase(unittest.TestCase):
    def test_datetime(self):
        now = datetime.datetime.now()
        obj = {
            'datetime': now
        }

        self.assertDictEqual(simplejson.loads(json_dumps(obj)), {
            'datetime': now.strftime('%d/%m/%Y %H:%M:%S')
        })

    def test_date(self):
        now = datetime.date.today()
        obj = {
            'date': now
        }

        self.assertDictEqual(simplejson.loads(json_dumps(obj)), {
            'date': now.strftime('%d/%m/%Y')
        })

    def test_time(self):
        now = datetime.datetime.now().time()

        obj = {
            'time': now,
        }

        self.assertDictEqual(simplejson.loads(json_dumps(obj)), {
            'time': now.strftime('%H:%M')
        })

    def test_set(self):
        value = set([1, 2, 3])

        obj = {
            'set': value,
        }

        self.assertDictEqual(simplejson.loads(json_dumps(obj)), {
            'set': [1, 2, 3],
        })

    def test_dict(self):
        value = {'a': 1, 'b': 2}

        obj = {
            'dict': value,
        }

        self.assertDictEqual(simplejson.loads(json_dumps(obj)), {
            'dict': value,
        })