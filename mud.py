#!/usr/bin/python

# mud.py - music deduplicator 
# Check for duplicates (e.g. differently encoded files of the same song) 
# in your music collection.

# Author: Isaac Hailperin <isaac.hailperin@gmail.com>
VERSION=0.1 # MAR-2015 | isaac | initial version

import argparse

def build_collection():
    """
    Go through the collection song by song and add them to the
    dejavu database, if it is not already recognized.

    In any case, create an entry in the song_files database, pointing
    to the song_id in dejavu.songs

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


###
# CLI
###
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(
        description = 'Check for duplicates in your music collection. mud will find \
            all duplicates, even if the file is encoded at a different bitrate. And \
            of course it won\'t be fooled by tags :)')
    parser.add_argument('-b','--build-collection',
        type = str,
        default = '',
        help = '')

