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

@register.tag
def stuff_info(parser, token):
    """
    {% stuff_info "file_path"|variable [as var] %}
    ritorna il mimetype e la dimensione del file specificato (il file deve
    risidere all'interno della dir "stuff")
    """
    contents = token.split_contents()
    tag_name = contents[0]
    try:
        fpath = contents[1]
    except IndexError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    if len(contents) > 2:
        if len(contents) != 4 or contents[-2] != 'as':
            raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
        var_name = contents[-1]
    else:
        var_name = None

    class StuffInfoNode(template.Node):
        def __init__(self, fpath, var_name):
            if fpath.startswith('"') and fpath.endswith('"'):
                self.fpath = fpath[1:-1]
            else:
                self.fpath = template.Variable(fpath)
            self.var_name = var_name
        def render(self, context):
            try:
                fpath = self.fpath.resolve(context)
            except AttributeError:
                fpath = self.fpath
            try:
                fpath = fpath.path
            except AttributeError:
                fpath = os.path.join(settings.STUFF_DIR, fpath)
            try:
                stat = os.stat(fpath)
            except (AttributeError, OSError), e:
                fsize = ftype = None
            else:
                fsize = stat.st_size
                ftype = mimetypes.guess_type(fpath)[0]
            if self.var_name:
                context[self.var_name] = (ftype, fsize)
                return ''
            else:
                return "(%s %s)" % (ftype, fsize)
            
    return StuffInfoNode(fpath, var_name)

@register.tag
def conference_speakers(parser, token):
    """
    {% conference_speakers [ conference ] as var %}
    inserisce in var l'elenco degli speaker (opzionalmente è possibile
    filtrare per conferenza).
    """
    contents = token.split_contents()
    tag_name = contents[0]
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    if len(contents) > 3:
        conference = contents[1]
        raise template.TemplateSyntaxError("conference params not yet supported")
    else:
        conference = None
    
    class SpeakersNode(template.Node):
        def __init__(self, conference, var_name):
            self.var_name = var_name
            if conference:
                if conference.startswith('"') and conference.endswith('"'):
                    self.conference = conference[1:-1]
                else:
                    self.conference = template.Variable(conference)
            else:
                self.conference = None
        def render(self, context):
            speakers = models.Speaker.objects.all()
            context[self.var_name] = speakers
            return ''
    return SpeakersNode(conference, var_name)

class TNode(template.Node):
    def _set_var(self, v):
        if not v:
            return v
        if v.startswith('"') and v.endswith('"'):
            return v[1:-1]
        else:
            return template.Variable(v)

    def _get_var(self, v, context):
        try:
            return v.resolve(context)
        except AttributeError:
            return v


@register.tag
def conference_talks(parser, token):
    """
    {% conference_talks [ speaker ] [ conference ] as var %}
    inserisce in var l'elenco dei talk (opzionalmente è possibile
    filtrare per speaker e conferenza).
    """
    contents = token.split_contents()
    tag_name = contents[0]
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    contents = contents[1:-2]

    speaker = conference = None
    if contents:
        speaker = contents.pop(0)
    if contents:
        conference = contents.pop(0)
    
    class TalksNode(TNode):
        def __init__(self, speaker, conference, var_name):
            self.var_name = var_name
            self.speaker = self._set_var(speaker)
            self.conference = self._set_var(conference)
        
        def render(self, context):
            talks = models.Talk.objects.all()
            speaker = self._get_var(self.speaker, context)
            conference = self._get_var(self.conference, context)
            if speaker:
                talks = talks.filter(speaker = speaker)
            context[self.var_name] = talks
            return ''
    return TalksNode(speaker, conference, var_name)

@register.filter
def split(value, arg):
    return value.split(arg)

@register.filter
def splitonspace(value):
    return value.split(' ')

@register.filter
def splitbysize(value, arg):
    from itertools import izip
    def grouper(n, iterable, fillvalue=None):
        "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * n
        return list(izip(*args))
    arg = int(arg)
    value = list(value)
    if len(value) % arg:
        value += [ None ] * (arg - (len(value) % arg))
    return grouper(arg, value)

@register.tag
def conference_sponsor(parser, token):
    """
    {% conference_sponsor [ conference ] as var %}
    """
    contents = token.split_contents()
    tag_name = contents[0]
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    contents = contents[1:-2]

    conference = None
    if contents:
        conference = contents.pop(0)

    class SponsorNode(TNode):
        def __init__(self, conference, var_name):
            self.var_name = var_name
            self.conference = self._set_var(conference)

        def render(self, context):
            sponsor = models.Sponsor.objects.all()
            conference = self._get_var(self.conference, context)
            if conference:
                sponsor = sponsor.filter(sponsorincome__conference = conference)
                sponsor = sponsor.order_by('-sponsorincome__income', 'sponsor')
            context[self.var_name] = sponsor
            return ''
    return SponsorNode(conference, var_name)
