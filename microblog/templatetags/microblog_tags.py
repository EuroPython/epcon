# -*- coding: UTF-8 -*-
import re
from collections import defaultdict
from datetime import date

from django import template
from django.contrib.sites.models import Site
from django.template import Context
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext
from django.utils.safestring import mark_safe

from microblog import dataaccess
from microblog import models
from microblog import settings

from fancy_tag import fancy_tag

register = template.Library()

def _lang(ctx):
    try:
        l = ctx['LANGUAGE_CODE']
    except KeyError:
        l = settings.MICROBLOG_DEFAULT_LANGUAGE
    return l.split('-', 1)[0]

@fancy_tag(register, takes_context=True)
def post_list(context, post_type='any', count=None, year=None, tag=None, category=None, author=None):
    posts = dataaccess.post_list(_lang(context))
    posts = settings.MICROBLOG_POST_FILTER(posts, context.get('user'))
    if post_type == 'featured':
        posts = filter(lambda x: x.featured, posts)
    elif post_type == 'non-featured':
        posts = filter(lambda x: not x.featured, posts)
    if year is not None:
        year = int(year)
        posts = filter(lambda x: x.date.year == year, posts)
    if tag is not None:
        tagged = dataaccess.tagged_posts(tag)
        posts = filter(lambda x: x.id in tagged, posts)
    if category is not None:
        posts = filter(lambda x: x.category == category, posts)
    if author is not None:
        posts = filter(lambda x: x.author == author, posts)
    if count is not None:
        posts = posts[:count]
    return posts

@fancy_tag(register, takes_context=True)
def year_list(context):
    posts = post_list(context)
    years = defaultdict(lambda: 0)
    for p in posts:
        years[date(day=1, month=1, year=p.date.year)] += 1
    return sorted(years.items())

@fancy_tag(register, takes_context=True)
def month_list(context):
    posts = post_list(context)
    months = defaultdict(lambda: 0)
    for p in posts:
        months[date(day=1, month=p.date.month, year=p.date.year)] += 1
    return sorted(months.items())

@fancy_tag(register, takes_context=True)
def author_list(context):
    posts = post_list(context)
    authors = defaultdict(lambda: 0)
    for p in posts:
        authors[p.author] += 1
    return sorted(authors.items(), key=lambda x: x[0].first_name + x[0].last_name)

@fancy_tag(register, takes_context=True)
def category_list(context):
    posts = post_list(context)
    categories = defaultdict(lambda: 0)
    for p in posts:
        categories[p.category] += 1
    return sorted(categories.items(), key=lambda x: x[0].name)

@fancy_tag(register, takes_context=True)
def tags_list(context):
    posts = post_list(context)
    tmap = dataaccess.tag_map()
    tags = defaultdict(lambda: 0)
    for p in posts:
        for t in tmap.get(p.id, []):
            tags[t.name] += 1
    return sorted(tags.items())

@fancy_tag(register, takes_context=True)
def opengraph_meta(context, pid):
    post_data = dataaccess.post_data(pid, _lang(context))
    meta = (
        ('og:title', post_data['content'].headline),
        ('og:type', 'article'),
        ('og:url', post_data['url']),
        ('og:image', post_data['post'].image),
        ('article:published_time', post_data['post'].date.isoformat()),
        ('article:section', post_data['post'].category.name),
        ('article:tag', post_data['tags']),
        ('article:author:first_name', post_data['post'].author.first_name),
        ('article:author:last_name', post_data['post'].author.last_name),
    )
    html = []
    for key, value in meta:
        if not isinstance(value, list):
            value = [value]
        html.extend(['<meta property="%s" content="%s" />' % (key, v) for v in value])
    return mark_safe('\n'.join(html))

@register.filter
def post_tags(post):
    tmap = dataaccess.tag_map()
    return tmap[post.id]

@fancy_tag(register, takes_context=True)
def get_post_data(context, pid):
    return dataaccess.post_data(pid, _lang(context))

@fancy_tag(register, takes_context=True)
def get_post_comment(context, post):
    data = dataaccess.post_data(post.id, _lang(context))
    return data['comments']

@register.inclusion_tag('microblog/show_posts_list.html', takes_context=True)
def show_posts_list(context, posts):
    ctx = Context(context)
    ctx.update({
        'posts': posts,
    })
    return ctx

@register.inclusion_tag('microblog/show_post_summary.html', takes_context=True)
def show_post_summary(context, post):
    ctx = Context(context)
    ctx.update(dataaccess.post_data(post.id, _lang(context)))
    return ctx

@register.inclusion_tag('microblog/show_post_detail.html', takes_context=True)
def show_post_detail(context, content, options=None):
    if context['user'].is_anonymous() and not content.post.is_published():
        return {}
    context.update({
        'post': content.post,
        'options': options,
        'content': content,
    })
    return context

@register.inclusion_tag('microblog/show_social_networks.html', takes_context=True)
def show_social_networks(context, content):
    request = context['request']
    site = Site.objects.get_current()
    context.update({
        'post': content.post,
        'content': content,
        'content_url': 'http://%s%s' % (site.domain, content.get_absolute_url()),
    })
    return context

@register.inclusion_tag('microblog/trackback_rdf.xml')
def trackback_rdf(content):
    return {
        'content': content if settings.MICROBLOG_TRACKBACK_SERVER else None,
    }

@register.inclusion_tag('microblog/show_reactions_list.html')
def show_reactions_list(content):
    return {
        'reactions': dataaccess.get_reactions(content.id),
    }

last_close = re.compile(r'(</[^>]+>)$')

@register.filter
def prepare_summary(content):
    """
    Aggiunge al summary il link continua che punta al body del post
    """
    summary = content.summary
    if not content.body:
        return summary
    data = dataaccess.post_data(content.post_id, content.language)
    continue_string = ugettext("Continua")
    link = '<span class="continue"> <a href="%s">%s&nbsp;&rarr;</a></span>' % (data['url'], continue_string)
    # se il summary contiene del markup cerco di inserire il link dentro il tag
    # più esterno
    match = last_close.search(summary)
    if match:
        match = match.group(1)
        summary = summary[:-len(match)] + link + summary[-len(match):]
    else:
        summary += link
    return summary

@register.filter
def user_name_for_url(user):
    """
    """
    return slugify('%s-%s' % (user.first_name, user.last_name))

@register.inclusion_tag('microblog/show_post_comments.html', takes_context=True)
def show_post_comments(context, post):
    ctx = Context(context)
    ctx.update({
        'post': post,
    })
    return ctx

@register.filter
def post_published(q, lang):
    """
    Filtra i post passati lasciando solo quelli pubblicabili.
    """
    # TODO: al momento q può essere solo un queryset, bisognerebbe prevedere il
    # caso in cui q sia un iterable di post
    return models.Post.objects.published(q=q, lang=lang)
