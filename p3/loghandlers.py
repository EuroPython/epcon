#-*- coding: utf-8 -*-
import codecs
import logging
import logging.handlers
import socket
# SysLogHandler con patch per utf-8
# http://bugs.python.org/issue7077
# http://svn.python.org/view/python/trunk/Lib/logging/handlers.py?r1=75586&r2=75585&pathrev=75586&view=patch
class SysLogHandlerPatched(logging.handlers.SysLogHandler):
    def emit(self, record):
        """
        Emit a record.

        The record is formatted, and then sent to the syslog server. If
        exception information is present, it is NOT sent to the server.
        """
        msg = self.format(record)
        """
        We need to convert record level to lowercase, maybe this will
        change in the future.
        """
        msg = self.log_format_string % (
            self.encodePriority(self.facility,
                                self.mapPriority(record.levelname)),
                                msg)
        # Treat unicode messages as required by RFC 5424
        if type(msg) is unicode:
            msg = msg.encode('utf-8')
            #if codecs:
            #    msg = codecs.BOM_UTF8 + msg
        try:
            if self.unixsocket:
                try:
                    self.socket.send(msg)
                except socket.error:
                    self._connect_unixsocket(self.address)
                    self.socket.send(msg)
            else:
                self.socket.sendto(msg, self.address)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

