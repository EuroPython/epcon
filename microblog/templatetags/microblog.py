# -*- coding: UTF-8 -*-
from __future__ import absolute_import
from django import template
from microblog import models

register = template.Library()

@register.inclusion_tag('microblog/show_post_summary.html', takes_context=True)
def show_post_summary(context, post):
    lang = context['LANGUAGE_CODE']
    contents = dict((c.language, c) for c in post.postcontent_set.all())
    try:
        content = contents[lang]
        if not content.headline:
            raise KeyError()
    except KeyError:
        for l, c in contents.items():
            if c.headline:
                content = c
                break
        else:
            raise ValueError('There is no a valid content (in any language)')
    return {
        'post': post,
        'content': content
    }


@register.inclusion_tag('microblog/show_post_detail.html')
def show_post_detail(content):
    return {
        'post': content.post,
        'content': content
    }
