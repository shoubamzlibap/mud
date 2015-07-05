#!/usr/bin/python

# mud.py - music deduplicator
# Check for duplicates (e.g. differently encoded files of the same song)
# in your music collection.

# Author: Isaac Hailperin <isaac.hailperin@gmail.com>
VERSION = 0.1  # APR-2015 | isaac | initial version

import argparse
import os
from MySQLdb import IntegrityError
import warnings
import eyed3
import settings

from dejavu import Dejavu
from dejavu.database_sql import SQLDatabase, cursor_factory, DictCursor
from dejavu.recognize import FileRecognizer
import pydub

ERROR_CODES = {
    'CouldntDecodeError': -1,
    'SongObjectIsNone': -2,
    }

class MudDatabase(SQLDatabase):

    """
    Shamelessly stealing database code from dejavu.
    """
    # tables
    SONGFILES_TABLENAME = "songfiles"

    # fields
    FIELD_FILE_ID = 'file_id'  # primary key, autoincrement
    FIELD_FILE_PATH = 'file_path'
    FIELD_FILE_ERROR = 'file_error'
    FIELD_SONG_ID = SQLDatabase.FIELD_SONG_ID  # foreign key -> songs, song_id
    FIELD_SONG_ARTIST = 'song_artist'
    FIELD_SONG_TITLE = 'song_title'
    FIELD_SONG_ALBUM = 'song_album'

    # creates
    CREATE_SONGFILES_TABLE = """
        CREATE TABLE IF NOT EXISTS `%s` (
             `%s` mediumint unsigned not null auto_increment,
             `%s` varchar(500) not null unique,
             `%s` mediumint unsigned,
             `%s` smallint default '0',
             `%s` varchar(250),
             `%s` varchar(250),
             `%s` varchar(250),
         INDEX (%s,%s),
         UNIQUE KEY `unique_constraint` (%s, %s),
         FOREIGN KEY (%s) REFERENCES %s(%s) ON DELETE CASCADE
    ) ENGINE=INNODB;""" % (
        SONGFILES_TABLENAME,
        FIELD_FILE_ID,
        FIELD_FILE_PATH,
        FIELD_SONG_ID,
        FIELD_FILE_ERROR,
        FIELD_SONG_ARTIST,
        FIELD_SONG_TITLE,
        FIELD_SONG_ALBUM,
        FIELD_FILE_PATH, FIELD_SONG_ID,  # index
        FIELD_FILE_ID, FIELD_FILE_PATH,  # uniq keys
        FIELD_SONG_ID, SQLDatabase.SONGS_TABLENAME, FIELD_SONG_ID  # forein key

    )

    # inserts
    INSERT_SONGFILE = """
        INSERT INTO %s (%s) values
        (%%s); """ % (SONGFILES_TABLENAME, FIELD_FILE_PATH)

    # updates
    UPDATE_SONGFILE = """
        UPDATE %s SET %s=%%s,
        %s=%%s, %s=%%s, %s=%%s
        WHERE %s=%%s;""" % (SONGFILES_TABLENAME, FIELD_SONG_ID,
                            FIELD_SONG_ARTIST, FIELD_SONG_TITLE,
                            FIELD_SONG_ALBUM, FIELD_FILE_PATH)

    UPDATE_ERROR_SONGFILE = """
        UPDATE %s SET %s=%%s,
        %s=%%s, %s=%%s, %s=%%s
        WHERE %s=%%s;""" % (SONGFILES_TABLENAME, FIELD_FILE_ERROR,
                            FIELD_SONG_ARTIST, FIELD_SONG_TITLE,
                            FIELD_SONG_ALBUM, FIELD_FILE_PATH)

    # selects
    SELECT_NEW_FILES = """
        SELECT %s FROM %s WHERE %s is NULL;
        """ % (FIELD_FILE_PATH, SONGFILES_TABLENAME, FIELD_SONG_ID)

    SELECT_SONG_IDS = """ SELECT %s FROM %s
        ;""" % (FIELD_SONG_ID, SQLDatabase.SONGS_TABLENAME)

    SELECT_FILE_BY_ID = """
        SELECT %s,%s,
        %s,%s FROM %s WHERE %s=%%s
        """ % (FIELD_FILE_PATH, FIELD_SONG_ARTIST,
               FIELD_SONG_TITLE, FIELD_SONG_ALBUM,
               SONGFILES_TABLENAME, FIELD_SONG_ID)

    SELECT_ALL_FILES = """ SELECT %s FROM %s;
        """ % (FIELD_FILE_PATH, SONGFILES_TABLENAME)

    SELECT_NUM_FILES = """SELECT COUNT(*), 'num_files' FROM %s;
        """ % (SONGFILES_TABLENAME)

    SELECT_NUM_FINGERPRINTED = """SELECT COUNT(*), 'num_fingerprinted' FROM 
        %s WHERE %s IS NOT NULL; """ % (SONGFILES_TABLENAME, FIELD_SONG_ID)

    SELECT_NUM_ERRORS = """SELECT COUNT(*), 'num_errors' 
        FROM %s WHERE %s = %%s; """ % (SONGFILES_TABLENAME, FIELD_FILE_ERROR)

    # deletes
    DELETE_SONG_FILE = """
        DELETE FROM %s WHERE %s=%%s
        ;""" % (SONGFILES_TABLENAME, FIELD_FILE_PATH)

    def __init__(self, **options):
        """
        Setup Database code
        """
        self.cursor = cursor_factory(**options)

    def setup(self):
        """
        Creates any non-existing tables required for mud to function.

        This also removes all songs that have been added but have no
        fingerprints associated with them.
        """
        # first calling dejavu setup, as we depend on these databases
        super(MudDatabase, self).setup()
        with self.cursor() as cur:
            cur.execute(self.CREATE_SONGFILES_TABLE)

    def insert_songfile(self, file_path):
        """
        Insert a song file into the database

        file_path: string, full path of file
        """
        with self.cursor() as cur:
            cur.execute(self.INSERT_SONGFILE, [file_path])

    def update_songfile(self, file_path, song_id, artist, title, album):
        """
        Update a songfile with its song id.

        file_path: string, full path of file
        song_id: int, id of a fingerprinted song
        artist: string, content of correspondint id3 tag
        title: string, content of correspondint id3 tag
        album: string, content of correspondint id3 tag

        """
        with self.cursor() as cur:
            cur.execute(self.UPDATE_SONGFILE, [
                song_id, artist, title, album, file_path])

    def update_error_on_songfile(self, file_path, artist, title, album, error_code=0):
        """
        Set error code on song file.

        file_path: string, full path of file
        artist: string, content of correspondint id3 tag
        title: string, content of correspondint id3 tag
        album: string, content of correspondint id3 tag
        error_code: int, an error code, currently just {0: 'no error', 1: 'no song_id'}

        """
        with self.cursor() as cur:
            cur.execute(self.UPDATE_ERROR_SONGFILE, [
                error_code, artist, title, album, file_path])

    def select_new_files(self):
        """
        Select all files without a song ID
        """
        with self.cursor(cursor_type=DictCursor) as cur:
            cur.execute(self.SELECT_NEW_FILES)
            for row in cur:
                yield row

    def select_song_ids(self):
        """
        Get all song IDs
        """
        with self.cursor(cursor_type=DictCursor) as cur:
            cur.execute(self.SELECT_SONG_IDS)
            for row in cur:
                yield row

    def select_file_by_id(self, song_id):
        """
        Get songfile by id

        song_id: int, id of a fingerprinted song
        """
        with self.cursor(cursor_type=DictCursor) as cur:
            cur.execute(self.SELECT_FILE_BY_ID, [song_id])
            for row in cur:
                yield row

    def select_all_song_files(self):
        """Get all song files stored in db."""
        with self.cursor(cursor_type=DictCursor) as cur:
            cur.execute(self.SELECT_ALL_FILES, [])
            for row in cur:
                yield row

    def select_num_files(self):
        """Get the number of files indexed"""
        with self.cursor(cursor_type=DictCursor) as cur:
            cur.execute(self.SELECT_NUM_FILES, [])
            for row in cur:
                return row['COUNT(*)']

    def select_num_fingerprinted(self):
        """Get the number of files fingerprinted"""
        with self.cursor(cursor_type=DictCursor) as cur:
            cur.execute(self.SELECT_NUM_FINGERPRINTED, [])
            for row in cur:
                return row['COUNT(*)']

    def select_num_errors(self, error_key):
        """
        Get the number of errors for the specified key
        
        error_key: string, must be a key to ERROR_CODES 

        """
        with self.cursor(cursor_type=DictCursor) as cur:
            cur.execute(self.SELECT_NUM_ERRORS, [ERROR_CODES[error_key]])
            for row in cur:
                return row['COUNT(*)']

    def delete_song_file(self, path):
        """
        Delete path from database.
        """
        with self.cursor() as cur:
            cur.execute(self.DELETE_SONG_FILE, [path])


# object for usage by functions below
warnings.filterwarnings('ignore')
db = MudDatabase(**settings.dejavu_config.get('database', {}))

def build_collection():
    """
    Go through the collection song by song and add them to the
    dejavu database, if it is not already recognized.

    In any case, create an entry in the song_files database, pointing
    to the song_id in dejavu.songs

    """
    iprint('Building collection')
    for song_f in list_new_files():
        song_id = get_song_id(song_f)
        add_to_collection(song_f, song_id)


def add_to_collection(song_file, song_id):
    """
    Add song_file to collection, with foreign key song_id

    song_file: string, absolute path to sound file
    song_id: int, foreign key to songs database

    """
    audio_file = eyed3.load(song_file)
    if audio_file.tag:
        artist = audio_file.tag.artist
        title = audio_file.tag.title
        album = audio_file.tag.album
        for tag_item in (artist, title, album):
            if tag_item:
                tag_item = tag_item.strip()
            else:
                tag_item = ''
    else:
        artist = ''
        title = os.path.split(song_file)[1].replace('.mp3','').replace('.MP3','')
        album = ''
    if song_id > 0:
        db.update_songfile(song_file, song_id, artist, title, album)
    else:
        db.update_error_on_songfile(song_file, artist, title, album, error_code=song_id)


def list_new_files():
    """
    Return a list of filenames from the database that are not yet fingerprinted.
    """
    for filepath in db.select_new_files():
        yield filepath['file_path']


def get_song_id(song_file):
    """
    Return song_id of song_file, fingerprint first if nessessary.

    song_file: string, absolute path to sound file
    """
    djv = Dejavu(settings.dejavu_config)
    song = None
    try:
        djv.fingerprint_file(song_file)
        song = djv.recognize(FileRecognizer, song_file)
    except pydub.exceptions.CouldntDecodeError:
        return ERROR_CODES['CouldntDecodeError']
    if song:
        return song['song_id']
    else:
        return ERROR_CODES['SongObjectIsNone']


def scan_files():
    """Scan for music files and add them to the database."""
    iprint('Scanning music base dir for mp3 files')
    for root, sub_folders, files in os.walk(settings.music_base_dir):
        for filepath in files:
            if filepath.endswith('.mp3') or filepath.endswith('.MP3'):
                add_song_file(os.path.join(root, filepath))


def add_song_file(song_file):
    """Add a song file to the database, if it not already exists."""
    try:
        db.insert_songfile(song_file)
    except IntegrityError:
        pass


def get_duplicates():
    """
    Query the database for duplicates.

    This is achived by going through all song_ids and then list
    all song_files that point to a certain song_id. Only
    return song_ids (together with the song_files) that have more
    then one song_file pointing to them.
    """
    duplicates = []
    for sid in db.select_song_ids():
        files = []
        for path in db.select_file_by_id(sid['song_id']):
            files.append(path)
        if len(files) > 1:
            duplicates.append(files)
    return duplicates


def print_duplicates():
    """ Print duplicates to std out """
    dups = get_duplicates()
    if dups:
        for sfiles in dups:
            print
            for sound_file in sfiles:
                song_title = sound_file['song_title']
                if not song_title: song_title = 'NO TITLE'
                print song_title + ' - ' + sound_file['file_path']
    else:
        print 'No duplicates found'


def print_stats():
    """Print some statistics."""
    # Progress
    num_files = db.select_num_files()
    num_fingerprinted = db.select_num_fingerprinted()
    print 'PROGRESS: ' + str(num_fingerprinted) + ' of ' + str(num_files) + ' fingerprinted.'
    # Errors
    for error_key in ERROR_CODES.keys():
        num_errors = db.select_num_errors(error_key)
        print 'ERRORS: ' + str(num_errors) + ' ' + error_key
    # Duplicates
    dups = get_duplicates()
    print 'DUPLICATES: ' + str(len(dups)) + ' duplicates found'


def check_files():
    """
    Go through songfiles table and check if each file still exists on disk.
    """
    iprint('Checking all songs in database still exists on disk.')
    for song_file in db.select_all_song_files():
        if not os.path.isfile(song_file['file_path']):
            iprint('Deleting ' + song_file['file_path'] + ' from database.')
            db.delete_song_file(song_file['file_path'])


def iprint(message, level=2):
    """
    Print messages, honoring a verbosity level

    message: string, a message to be printed
    level: int, a verbosity level
    """
    general_level = 1  # should be moved to settings, and accessible via cli
    if level > general_level:
        print message

#
# CLI
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Check for duplicates in your music collection. mud will \
            find all duplicates, even if the file is encoded at a different \
            bitrate. And of course it won\'t be fooled by tags :)')
    parser.add_argument('-s', '--scan',
                        action='store_true',
                        help='Scan music directory for new files.')
    parser.add_argument('-b', '--build-collection',
                        action='store_true',
                        help='Go through collection and build database of \
                            audio fingerprints.')
    parser.add_argument('-p', '--print-dups',
                        action='store_true',
                        help='Print all duplicates found.')
    parser.add_argument('-t', '--print-stats',
                        action='store_true',
                        help='Print some statistics and progress information.')
    parser.add_argument('-c', '--check',
                        action='store_true',
                        help='Check if files in database still exist on disk.')
    parser.add_argument('-v', '--version',
                        action='store_true',
                        help='Display version.')
    args = parser.parse_args()

    db.setup()

    if args.version:
        print VERSION
        exit(0)
    if args.scan:
        scan_files()
    if args.build_collection:
        build_collection()
    if args.check:
        check_files()
    if args.print_dups:
        print_duplicates()
    if args.print_stats:
        print_stats()
