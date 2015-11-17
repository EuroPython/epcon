# -*- coding: utf-8 -*-
## Ispirato a {{{ http://code.activestate.com/recipes/52215/ (r1)
import sys, traceback
from cStringIO import StringIO

from django.conf import settings

def dump_exc_plus(exclude=None):
    """
    Returns a string containing the usual traceback information, followed by a
    listing of all the local variables in each frame, skipping the ones listed
    in exclude.
    """
    s = StringIO()

    traceback.print_exc(file=s)

    print >>s, "Locals by frame, innermost last"
    if exclude:
        print >>s, "  excluding '%s'" % "','".join(exclude)

    tb = sys.exc_info()[2]
    while tb:
        frame = tb.tb_frame
        tb = tb.tb_next

        print >>s
        print >>s, "Frame %s in %s at line %s" % (
            frame.f_code.co_name,
            frame.f_code.co_filename,
            frame.f_lineno)

        for key, value in frame.f_locals.items():
            if exclude and key in exclude:
                continue

            print >>s, "\t%20s = " % key,
            #We have to be careful not to cause a new error in our error
            #printer! Calling str() on an unknown object could cause an
            #error we don't want.
            try:
                print >>s, repr(value)
            except:
                print >>s,  "<ERROR WHILE PRINTING VALUE>"

    return s.getvalue()

class DebugInfo(object):
    """
    Adds user details to request context on receiving an exception, so that
    they show up in the error emails.

    Add to settings.MIDDLEWARE_CLASSES and keep it outermost(i.e. on top if
    possible). This allows it to catch exceptions in other middlewares as well.
    """
    def process_exception(self, request, exception):
        if settings.DEBUG:
            return
        try:
            request.META['_TRACEBACK'] = dump_exc_plus(exclude=('request', 'environ')).replace('\t', '    ').split('\n')
            if request.user:
                request.META['_USERNAME'] = str(request.user.username)
        except:
            pass
