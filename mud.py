#!/usr/bin/python

# mud.py - music deduplicator 
# Check for duplicates (e.g. differently encoded files of the same song) 
# in your music collection.

# Author: Isaac Hailperin <isaac.hailperin@gmail.com>
VERSION=0.1 # MAR-2015 | isaac | initial version

import argparse
import os
import settings

#from dejavu import Dejavu
#from dejavu.recognize import FileRecognizer
from dejavu.database_sql import SQLDatabase

class MudDatabase(SQLDatabase):
    """
    Shamelessly stealing database code from dejavu.
    """
    pass

def build_collection():
    """
    Go through the collection song by song and add them to the
    dejavu database, if it is not already recognized.

    In any case, create an entry in the song_files database, pointing
    to the song_id in dejavu.songs

    """
    for song_f in list_new_files():
        song_id = get_song_id(song_f)
        add_to_collection(song_f, song_id)

def add_to_collection(song_file, song_id):
    """
    Add song_file to collection, with foreign key song_id

    song_file: string, absolute path to sound file
    song_id: int, foreign key to songs database

    """
    pass


def list_new_files():
    """
    Return a list of filenames that are not yet fingerprinted.
    """
    pass

def get_song_id(song_file):
    """
    Return song_id of song_file, fingerprint first if nessessary.

    song_file: string, absolute path to sound file
    """
    pass

def scan_files():
    """
    Scan for music files and add them to the database
    """
    iprint('Scanning music base dir for mp3 files')
    file_list = []
    for root, sub_folders, files in os.walk(settings.music_base_dir):
        for f in files:
            if f.endswith('.mp3') or f.endswith('.MP3'):
                add_song_file(os.path.join(root,f))

def add_song_file(song_file):
    """
    Add a song file to the database, if it not already exists.
    """
    pass

def get_duplicates():
    """
    Query the database for duplicates.

    This is achived by going through all song_ids and then list
    all song_files that point to a certain song_id. Only
    return song_ids (together with the song_files) that have more
    then one song_file pointing to them.
    """
    pass

def iprint(message, level=2):
    """
    Print messages, honoring a verbosity level
    
    message: string, a message to be printed
    level: int, a verbosity level
    """
    general_level = 1 # should be moved to settings, and accessible via cli
    if level > general_level:
        print message

###
# CLI
###
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(
        description = 'Check for duplicates in your music collection. mud will find \
            all duplicates, even if the file is encoded at a different bitrate. And \
            of course it won\'t be fooled by tags :)')
    parser.add_argument('-b','--build-collection',
        action = 'store_true',
        help = 'Go through collection and build database')
    parser.add_argument('-s','--scan',
        action = 'store_true',
        help = 'Scan music directory for new files')
    args = parser.parse_args()
