# -*- coding: UTF-8 -*-
"""
Package contenente views/models e templatetags utili in più conferenze
pycon-like. Idealmente in questo package trovano posto la gestione di modelli
comuni (tipo le deadlines) templatetags di utilità (come la navigazione) e
codice particolare come l'accesso ad assopy. Questo package *non* dovrebbe
includere ne' template ne' file statici.
"""
import os.path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'deps'))

import models
import views
