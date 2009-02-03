# -*- coding: UTF-8 -*-
from __future__ import absolute_import
import mimetypes
import os
import os.path
import re
from django import template
from django.conf import settings

from conference import models
from pages import models as PagesModels

mimetypes.init()

register = template.Library()

class LatestDeadlinesNode(template.Node):
    """
    Inserisce in una variabile di contesto le deadlines presenti.
    Opzionalmente e' possibile specificare quante deadline si vogliono.

    Le deadline vengono riportate nella lingua dell'utente con un fallback
    nella lingua di default.
    """
    def __init__(self, limit, var_name):
        self.limit = limit
        self.var_name = var_name

    def render(self, context):
        query = models.Deadline.objects.valid_news()
        if self.limit:
            query = query[:self.limit]

        dlang = settings.LANGUAGES[0][0]
        lang = context.get('LANGUAGE_CODE', dlang)
        # le preferenze per la lingua sono:
        #   1. lingua scelta dall'utente
        #   2. lingua di default
        #   3. lingue in cui e' tradotta la deadline
        #
        # Se la traduzione di una deadline è vuota viene scartata
        # e provo la lingua successiva.
        # Se la deadline non ha alcuna traduzione (!) la scarto.
        news = []
        for n in query:
            contents = dict((c.language, c) for c in n.deadlinecontent_set.all())

            lang_try = (lang, dlang) + tuple(contents.keys())
            for l in lang_try:
                try:
                    content = contents[l]
                except KeyError:
                    continue
                if content.body:
                    break
            else:
                continue
            news.append((n.date, content.body))
        context[self.var_name] = news
        return ""

@register.tag
def latest_deadlines(parser, token):
    contents = token.split_contents()
    tag_name = contents[0]
    limit = None
    try:
        if contents[1] != 'as':
            try:
                limit = int(contents[1])
            except (ValueError, TypeError):
                raise template.TemplateSyntaxError("%r tag's argument should be an integer" % tag_name)
        else:
            limit = None
        if contents[-2] != 'as':
            raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
        var_name = contents[-1]
    except IndexError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    return LatestDeadlinesNode(limit, var_name)

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

# TODO: spostare in microblog
#from microblog import models as BlogModels
#class LastBlogPost(template.Node):
#    def __init__(self, var_name):
#        self.var_name = var_name
#
#    def render(self, context):
#        post = BlogModels.Post.objects.published()[0]
#        lang = context.get('LANGUAGE_CODE', settings.LANGUAGES[0][0])
#        context[self.var_name] = post
#        context[self.var_name + '_content'] = post.content(lang)
#        return ''
#        
#@register.tag
#def last_blog_post(parser, token):
#    contents = token.split_contents()
#    tag_name = contents[0]
#    if contents[-2] != 'as':
#        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
#    var_name = contents[-1]
#    return LastBlogPost(var_name)
#
