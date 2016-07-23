# -*- coding: UTF-8 -*-
from microblog import settings

def bitly_url(post_content):
    import bitly
    api = bitly.Api(login=settings.MICROBLOG_BITLY_LOGIN, apikey=settings.MICROBLOG_BITLY_APIKEY)
    return api.shorten(post_content.get_url())
