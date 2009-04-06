#!/usr/bin/python
# -*- encoding: utf-8 -*-
import sys
import urllib
import csv
import subprocess
from collections import defaultdict
from optparse import OptionParser


parser = OptionParser()
parser.add_option("-v", "--verbose", dest="verbose", action="store_true", default=None)

(options, args) = parser.parse_args()

try:
    input = urllib.urlopen(args[0])
except IndexError:
    input = urllib.urlopen("http://www.pycon.it/static/stuff/pycon3/votazione-pycon3.csv")

if options.verbose:
    log = lambda *args: sys.stdout.write('%s\n' % ' '.join(map(unicode, args)))
else:
    log = lambda *args: None

# FIXME: csv escaping bug
NUM_TALKS = 40
talknames = input.readline().strip()
talknames = talknames.replace("API, da Facebook", "API: da Facebook")
talknames = talknames.replace("buono,", "buono")
talknames = talknames.replace("brutto,", "brutto")
talknames = talknames.replace("Python, l'unione", "Python: l'unione")
talknames = talknames.split(",")[3:]
assert len(talknames) == NUM_TALKS

tie = range(NUM_TALKS)

try:
    proc = subprocess.Popen(["voteengine.py"],
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE)
except OSError, e:
    print u"voteengine.py non è presente nel path"
    sys.exit(1)

proc.stdin.write("-m schulze\n")
proc.stdin.write("-cands 0-%d " % (NUM_TALKS-1))
proc.stdin.write("-tie ")
proc.stdin.write(" ".join(map(str,tie)))
proc.stdin.write("\n")

votanti = 0
for vote in csv.reader(input):
    votanti += 1

    # Talk non votato: voto "3" d'ufficio
    vote = [x if x else "3" for x in vote]

    D = defaultdict(list)
    for idx,v in enumerate(vote[3:]):
        D[v].append(str(idx))
    rank = ">".join(
        filter(None,
               ("=".join(D["5"]),
                "=".join(D["4"]),
                "=".join(D["3"]),
                "=".join(D["2"]),
                "=".join(D["1"]))))
    log(vote[0], rank)

    # Peso doppio agli organizzatori
    peso = 1
    if vote[2] == "True":
        peso = 2

    for i in range(peso):
        proc.stdin.write(rank)
        proc.stdin.write("\n")

out,ret = proc.communicate()
log(out)

out = out.splitlines()
if ">" in out[-1]:
    classifica = out[-1].split(">")
    for x in classifica:
        x = int(x)
        print talknames[int(x)]
    log(out[-1])
    log("votanti:", votanti)

