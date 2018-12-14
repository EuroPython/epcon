from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse

from jinja2 import Environment


def environment(**options):
    # TODO(artcz)
    # there is some bug with pytest that passes debug as argument here and
    # jinja can't work it out. poping for now.
    if 'debug' in options:
        options.pop('debug')

    env = Environment(**options)
    env.globals.update({
        'static': staticfiles_storage.url,
        'url': reverse,
    })

    return env
