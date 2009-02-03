# -*- coding: UTF-8 -*-
from __future__ import absolute_import
import re
from django import template
from django.conf import settings
from microblog import models

register = template.Library()

class LastBlogPost(template.Node):
    def __init__(self, var_name):
        self.var_name = var_name

    def render(self, context):
        post = models.Post.objects.published()[0]
        lang = context.get('LANGUAGE_CODE', settings.LANGUAGES[0][0])
        context[self.var_name] = post
        context[self.var_name + '_content'] = post.content(lang)
        return ''
        
@register.tag
def last_blog_post(parser, token):
    contents = token.split_contents()
    tag_name = contents[0]
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    return LastBlogPost(var_name)

@register.inclusion_tag('microblog/show_post_summary.html', takes_context=True)
def show_post_summary(context, post):
    request = context['request']
    if context['user'].is_anonymous() and not post.is_published():
        return {}
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
        'content': content,
        'MEDIA_URL': context['MEDIA_URL'],
        'request': request,
    }

@register.inclusion_tag('microblog/show_post_detail.html', takes_context=True)
def show_post_detail(context, content, options=None):
    request = context['request']
    if context['user'].is_anonymous() and not content.post.is_published():
        return {}
    return {
        'post': content.post,
        'options': options,
        'content': content,
        'MEDIA_URL': context['MEDIA_URL'],
        'request': request,
    }

@register.inclusion_tag('microblog/show_social_networks.html', takes_context=True)
def show_social_networks(context, content):
    request = context['request']
    return {
        'post': content.post,
        'content': content,
        'content_url': 'http://%s%s' % (request.site.domain, content.get_absolute_url()),
        'MEDIA_URL': context['MEDIA_URL'],
        'request': request,
    }

class PostContent(template.Node):
    def __init__(self, arg, var_name):
        try:
            self.pid = int(arg)
        except ValueError:
            self.pid = template.Variable(arg)
        self.var_name = var_name

    def render(self, context):
        try:
            pid = self.pid.resolve(context)
        except AttributeError:
            pid = self.pid
        except template.VariableDoesNotExist:
            pid = None
        if pid:
            content = models.PostContent.objects.get(id = pid)
        else:
            content = None
        context[self.var_name] = content
        return ""

@register.tag
def get_post_content(parser, token):
    contents = token.split_contents()
    try:
        tag_name, arg, _, var_name = contents
    except ValueError:
        raise template.TemplateSyntaxError("%r tag's argument should be an integer" % contents[0])
    return PostContent(arg, var_name)


last_close = re.compile(r'(</[^>]+>)$')

@register.filter
def prepare_summary(postcontent):
    """
    Aggiunge al summary il link continua che punta al body del post
    """
    if not postcontent.body:
        return postcontent.summary
    summary = postcontent.summary
    link = '<span class="continue"> <a href="%s">[Continua]</a></span>' % postcontent.get_absolute_url()
    match = last_close.search(summary)
    if match:
        match = match.group(1)
        summary = summary[:-len(match)] + link + summary[-len(match):]
    else:
        summary += link
    return summary
