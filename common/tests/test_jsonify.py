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
