from django.template import Library
from fancy_tag import fancy_tag

register = Library()


@fancy_tag(register)
def say_soup(type_of_soup='Potato', size='regular'):
    if size != 'regular':
        return '%s Soup (%s)' % (type_of_soup, size)
    else:
        return '%s Soup' % type_of_soup


@fancy_tag(register)
def say_cheese(type_of_cheese, age_in_years):
    return 'Hooray for %s year old %s' % (age_in_years, type_of_cheese)


@fancy_tag(register)
def say_names(*args):
    return ', '.join(args)


@fancy_tag(register)
def say_languages(**kwargs):
    return ', '.join(['%s: %s' % (kw, v) for kw, v in kwargs.items()])


@fancy_tag(register, takes_context=True)
def say_hello(context, greeting):
    return u'%s, %s' % (greeting, context['user'])


@fancy_tag(register, takes_context=True)
def say_hello_like_a_chump(greeting):
    # Broken on purpose
    return u'%s, %s' % (greeting, context['?'])
