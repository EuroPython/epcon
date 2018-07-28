#!/usr/bin/env python



import sys
import jinja2

TEMPLATE = """from django.test import TestCase
from django.core.urlresolvers import reverse

class TestView(TestCase):
    {% for target, name in targets %}
    def test_{{ name|replace('-', '_') }}(self):
        # {{ name }} -> {{ target }}
        url = reverse('{{ name }}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    {% endfor %}
"""

env = jinja2.Environment()

targets = [line.strip().split() for line in sys.stdin]

tpl = env.from_string(TEMPLATE)
print(tpl.render(targets=targets))
    
