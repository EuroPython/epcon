# -*- coding: UTF-8 -*-
from __future__ import absolute_import
import re
from django import template
from django.conf import settings

from p3 import models
from pages import models as PagesModels
from microblog import models as BlogModels

register = template.Library()

class LatestNewsNode(template.Node):
    def __init__(self, limit, var_name):
        self.limit = limit
        self.var_name = var_name

    def render(self, context):
        query = models.Deadline.objects.valid_news()
        if self.limit:
            query = query[:self.limit]
        lang = context.get('LANGUAGE_CODE', settings.LANGUAGES[0][0])
        news = []
        for n in query:
            try:
                contents = n.deadlinecontent_set.get(language = lang)
            except models.DeadlineContent.DoesNotExist:
                continue
            news.append((n.date, contents.body))
        context[self.var_name] = news
        return ""

@register.tag
def latest_news(parser, token):
    contents = token.split_contents()
    tag_name = contents[0]
    try:
        limit = int(contents[1])
    except IndexError:
        limit = None
    except (ValueError, TypeError):
        raise template.TemplateSyntaxError("%r tag's argument should be an integer" % tag_name)
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    return LatestNewsNode(limit, var_name)

class NaviPages(template.Node):
    def __init__(self, page_type, var_name):
        self.page_type = page_type
        self.var_name = var_name

    def render(self, context):
        request = context['request']
        site = request.site
        query = PagesModels.Page.objects.navigation(site).order_by('tree_id', 'lft')
        query = query.filter(tags__contains = self.page_type)
        context[self.var_name] = query
        return ''

def navi_pages(parser, token):
    contents = token.split_contents()
    tag_name = contents[0]
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    return NaviPages(tag_name.split('_')[1], var_name)

register.tag('navi_menu1_pages', navi_pages)
register.tag('navi_menu2_pages', navi_pages)
register.tag('navi_menu3_pages', navi_pages)

class LastBlogPost(template.Node):
    def __init__(self, var_name):
        self.var_name = var_name

    def render(self, context):
        post = BlogModels.Post.objects.latest()
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

@register.inclusion_tag('p3/box_pycon_italia.html')
def box_pycon_italia():
    return {}

@register.inclusion_tag('p3/box_newsletter.html')
def box_newsletter():
    return {}
