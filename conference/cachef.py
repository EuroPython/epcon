# -*- coding: UTF-8 -*-
from django.core.cache import cache
from django.db.models.signals import pre_delete, post_save
from django.dispatch import Signal
import functools
import hashlib

try:
    from inspect import getcallargs
except ImportError:
    import sys
    from inspect import getargspec, ismethod

    def getcallargs(func, *positional, **named):
        """Get the mapping of arguments to values.

        A dict is returned, with keys the function argument names (including the
        names of the * and ** arguments, if any), and values the respective bound
        values from 'positional' and 'named'."""
        args, varargs, varkw, defaults = getargspec(func)
        f_name = func.__name__
        arg2value = {}

        # The following closures are basically because of tuple parameter unpacking.
        assigned_tuple_params = []
        def assign(arg, value):
            if isinstance(arg, str):
                arg2value[arg] = value
            else:
                assigned_tuple_params.append(arg)
                value = iter(value)
                for i, subarg in enumerate(arg):
                    try:
                        subvalue = next(value)
                    except StopIteration:
                        raise ValueError('need more than %d %s to unpack' %
                                        (i, 'values' if i > 1 else 'value'))
                    assign(subarg,subvalue)
                try:
                    next(value)
                except StopIteration:
                    pass
                else:
                    raise ValueError('too many values to unpack')
        def is_assigned(arg):
            if isinstance(arg,str):
                return arg in arg2value
            return arg in assigned_tuple_params
        if ismethod(func) and func.im_self is not None:
            # implicit 'self' (or 'cls' for classmethods) argument
            positional = (func.im_self,) + positional
        num_pos = len(positional)
        num_total = num_pos + len(named)
        num_args = len(args)
        num_defaults = len(defaults) if defaults else 0
        for arg, value in zip(args, positional):
            assign(arg, value)
        if varargs:
            if num_pos > num_args:
                assign(varargs, positional[-(num_pos-num_args):])
            else:
                assign(varargs, ())
        elif 0 < num_args < num_pos:
            raise TypeError('%s() takes %s %d %s (%d given)' % (
                f_name, 'at most' if defaults else 'exactly', num_args,
                'arguments' if num_args > 1 else 'argument', num_total))
        elif num_args == 0 and num_total:
            if varkw:
                if num_pos:
                    # XXX: We should use num_pos, but Python also uses num_total:
                    raise TypeError('%s() takes exactly 0 arguments '
                                    '(%d given)' % (f_name, num_total))
            else:
                raise TypeError('%s() takes no arguments (%d given)' %
                                (f_name, num_total))
        for arg in args:
            if isinstance(arg, str) and arg in named:
                if is_assigned(arg):
                    raise TypeError("%s() got multiple values for keyword "
                                    "argument '%s'" % (f_name, arg))
                else:
                    assign(arg, named.pop(arg))
        if defaults:    # fill in any missing values with the defaults
            for arg, value in zip(args[-num_defaults:], defaults):
                if not is_assigned(arg):
                    assign(arg, value)
        if varkw:
            assign(varkw, named)
        elif named:
            unexpected = next(iter(named))
            if isinstance(unexpected, unicode):
                unexpected = unexpected.encode(sys.getdefaultencoding(), 'replace')
            raise TypeError("%s() got an unexpected keyword argument '%s'" %
                            (f_name, unexpected))
        unassigned = num_args - len([arg for arg in args if is_assigned(arg)])
        if unassigned:
            num_required = num_args - num_defaults
            raise TypeError('%s() takes %s %d %s (%d given)' % (
                f_name, 'at least' if defaults else 'exactly', num_required,
                'arguments' if num_required > 1 else 'argument', num_total))
        return arg2value

WEEK = 7 * 24 * 60 * 60

cache_invalidated = Signal(providing_args=['keys'])

class CacheFunction(object):
    CACHE_MISS = object()

    def __init__(self, prefix='', timeout=WEEK, fhash=None, fkey=None):
        self.prefix = prefix
        self.timeout = timeout
        if fhash is None:
            fhash = self.hash_key
        self.fhash = fhash
        if fkey is None:
            fkey = self.generate_key
        self.fkey = fkey

    def __call__(self, *args, **kwargs):
        if args:
            if kwargs or not callable(args[0]):
                raise TypeError("invalid usage")
            return self._decorator(args[0])
        else:
            return functools.partial(self._decorator, **kwargs)

    def _decorator(self, func, invalidate=None, key=None, signals=(), models=(), timeout=None):
        if key is None:
            key = func.__name__
            if invalidate is None:
                invalidate = (func.__name__,)
        if timeout is None:
            timeout = self.timeout

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            k = self.fhash(self.fkey(key, func, args, kwargs))
            data = cache.get(k, self.CACHE_MISS)
            if data is self.CACHE_MISS:
                data = func(*args, **kwargs)
                cache.set(k, data, timeout)
            return data

        if invalidate:
            def iwrapper(sender, **kwargs):
                try:
                    keys = kwargs['cache_keys']
                except KeyError:
                    if callable(invalidate):
                        keys = invalidate(sender, **kwargs)
                    else:
                        keys = invalidate
                if keys:
                    if isinstance(keys, basestring):
                        keys = (keys,)
                    prefixed = [ self.prefix + k for k in keys ]
                    cache.delete_many(map(self.fhash, prefixed))
                    wrapper.invalidated.send(wrapper, cache_keys=keys)

            for s in signals:
                s.connect(iwrapper, weak=False)

            for m in models:
                post_save.connect(iwrapper, sender=m, weak=False)
                pre_delete.connect(iwrapper, sender=m, weak=False)

        def get_from_cache(fargs):
            cache_keys = {}
            for ix, farg in enumerate(fargs):
                if isinstance(farg, (list, tuple))\
                    and len(farg) == 2\
                    and isinstance(farg[0], (list, tuple))\
                    and isinstance(farg[1], dict):
                    args, kwargs = farg
                elif isinstance(farg, dict):
                    args = ()
                    kwargs = farg
                else:
                    args = farg
                    kwargs = {}
                k = self.fhash(self.fkey(key, func, args, kwargs))
                cache_keys[k] = (ix, farg)

            results = cache.get_many(cache_keys.keys())
            output = [ self.CACHE_MISS ] * len(fargs)
            for k, v in cache_keys.items():
                ix = v[0]
                try:
                    output[ix] = results[k]
                except KeyError:
                    pass
            return output
        wrapper.get_from_cache = get_from_cache
        wrapper.invalidated = Signal(providing_args=['cache_keys'])
        return wrapper

    def hash_key(self, key):
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        return hashlib.md5(key).hexdigest()

    def generate_key(self, key, func, args, kwargs):
        if callable(key):
            return key(func, *args, **kwargs)
        cargs = getcallargs(func, *args, **kwargs)
        try:
            k = key % args
        except TypeError:
            k = key % cargs
        return self.prefix + k
