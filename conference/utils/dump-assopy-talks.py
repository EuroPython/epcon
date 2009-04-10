#!/usr/bin/python
# -*- coding: utf-8 -*-

HOST = 'localhost'
DBNAME = 'assopy09'
USER = 'assopy'
PASSWORD = 'assopy'
SPEAKER_IMG = '/home/assopy/genro/data/sites/assopy09/data/speakers'

import sys
import psycopg2
from xml.etree import cElementTree as ET
import os.path
import zipfile

_speakers = []

def list_talk():
    query = """
        SELECT t.id, e.code, t.title
        FROM conference.conference_talk t INNER JOIN conference.conference_track tt
            ON t.track_id = tt.id
        INNER JOIN conference.conference_event e
            ON tt.event_id = e.id
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    for row in rows:
        print '%s ! %s %s' % row

def extract_talk(id):
    qtalk = """
        SELECT t.title, t.duration, t.language, t.abstract, t.abstract_en, t.subject, t.main_speaker_id, e.code
        FROM conference.conference_talk t INNER JOIN conference.conference_track tt
            ON t.track_id = tt.id
        INNER JOIN conference.conference_event e
            ON tt.event_id = e.id
        WHERE t.id=%s
    """
    qspk = """
        SELECT crd.first_name, crd.www, spk.activity, spk.area,
            crd.city, crd.state, spk.resume, spk.resume_en, crd.last_name, crd.card_name,
            usr.username
        FROM conference.conference_speaker spk INNER JOIN conference.conference_card crd
            ON spk.card_id = crd.id
        INNER JOIN adm.adm_user usr
            ON spk.user_id = usr.id
        WHERE spk.id=%s
    """
    cursor.execute(qtalk, (id,))
    talks = cursor.fetchall()
    enc = lambda x: unicode(x or '', 'utf-8')
    T = ET.Element('talk')
    for talk in talks:
        ET.SubElement(T, 'title').text = enc(talk[0])
        ET.SubElement(T, 'conference').text = enc(talk[7])
        ET.SubElement(T, 'duration').text = str(talk[1])
        ET.SubElement(T, 'language').text = enc(talk[2])
        ET.SubElement(T, 'abstract', {'lang': 'it'}).text = enc(talk[3])
        ET.SubElement(T, 'abstract', {'lang': 'en'}).text = enc(talk[4])
        ET.SubElement(T, 'tags').text = enc(talk[5])
        cursor.execute(qspk, (talk[6],))
        speaker = cursor.fetchall()[0]
        S = ET.SubElement(T, 'speaker')
        name = '' if speaker[0] is None else speaker[0]
        if speaker[8] is not None:
            name += ' ' + speaker[8]
        if not name:
            name = speaker[9]
        _speakers.append(speaker[10])
        ET.SubElement(S, 'name').text = enc(name)
        ET.SubElement(S, 'homepage').text = enc(speaker[1])
        ET.SubElement(S, 'activity').text = enc(speaker[2])
        ET.SubElement(S, 'industry').text = enc(speaker[3])
        if speaker[5]:
            ET.SubElement(S, 'location').text = enc(speaker[4]) + '/' + enc(speaker[5])
        else:
            ET.SubElement(S, 'location').text = enc(speaker[4])
        ET.SubElement(S, 'bio', {'lang': 'it'}).text = enc(speaker[6])
        ET.SubElement(S, 'bio', {'lang': 'en'}).text = enc(speaker[7])

    return T
conn = psycopg2.connect(host=HOST, database=DBNAME, user=USER, password=PASSWORD)
try:
    cursor = conn.cursor()
    try:
        if '-l' in sys.argv:
            list_talk()
        else:
            root = ET.Element('talks')
            for line in sys.stdin:
                root.append(extract_talk(line.split('!')[0].strip()))
            sys.stdout.write(ET.tostring(root, 'utf-8'))
    finally:
        cursor.close()
finally:
    conn.close()

if SPEAKER_IMG:
    if os.path.exists('speakers.zip'):
        print >> sys.stderr, "speakers.zip already exists"
        sys.exit(1)
    zip = zipfile.ZipFile('speakers.zip', 'w')
    for img in _speakers:
        fpath = os.path.join(SPEAKER_IMG, img, '_speakerimg.jpg')
        if os.path.exists(fpath):
            zip.write(fpath, img + '.jpg')
    zip.close()
