# -*- coding: UTF-8 -*-
class RisingResponse(object):
    """
    Questo middleware permette ad una vista di chiamare `RisingResponse.stop()`
    per interrompere l'esecuzione corrente.
    """

    class Response(Exception):
        def __init__(self, response):
            self.response = response

    @classmethod
    def stop(cls, r):
        raise cls.Response(r)

    def process_exception(self, request, exception):
        if isinstance(exception, self.Response):
            return exception.response
