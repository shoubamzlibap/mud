#!/usr/bin/python
"""
mud.py - music deduplicator
Check for duplicates (e.g. differently encoded files of the same song)
in your music collection.
"""

# Author: Isaac Hailperin <isaac.hailperin@gmail.com>
#VERSION = 0.1  # APR-2015 | isaac | initial version
#VERSION = '0.1.1'  # JUL-2015 | isaac | some fixes for fedora 22 and utf8 encoding
#VERSION = '0.2.0'  # JUL-2015 | isaac | logfile and stderr with different levels configurable
#VERSION = '0.2.1'  # AUG-2015 | isaac | fix for Exceptions thrown by eyed3
VERSION = '0.3.0'  # MAR-2016 | isaac | finding duplicate albums

import argparse
import collections
import logging
from MySQLdb import IntegrityError
import os
import settings
import warnings

from dejavu import Dejavu
from dejavu.database_sql import SQLDatabase, cursor_factory, DictCursor
from dejavu.recognize import FileRecognizer
import pydub
from multiprocessing import Process
from multiprocessing import Queue as MPQueue 

# unset eyed3 global log configuration
# https://bitbucket.org/nicfit/eyed3/issues/91/dont-configure-global-logging-settings
import eyed3
logging.getLogger().handlers.pop()
logging.setLoggerClass(logging.Logger)

# eyed3 expects a verbose log level and function. So here we go, copying the
# code from eyed3.utils.log
# Add some levels
logging.VERBOSE = logging.DEBUG + 1
logging.addLevelName(logging.VERBOSE, "VERBOSE")

class Logger(logging.Logger):
    '''Base class for all loggers'''

    def __init__(self, name):
        logging.Logger.__init__(self, name)

        # Using propogation of child to parent, by default
        self.propagate = True
        self.setLevel(logging.NOTSET)

    def verbose(self, msg, *args, **kwargs):
        '''Log \a msg at 'verbose' level, debug < verbose < info'''
        self.log(logging.VERBOSE, msg, *args, **kwargs)


logging.setLoggerClass(Logger)
# end from eyed3

logger = logging.getLogger('mud')
logger.setLevel(logging.DEBUG)

LOG_LEVELS = {
    'info': logging.INFO,
    'debug': logging.DEBUG,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL, }

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
        #super(MudDatabase, self).__init__(**options)

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


class mud(object):
    """A mud instance with its database"""

    def __init__(self, inst_num):
        """
        Initialize the database and create a Dejavu object

        inst_num: the number of the instance - 0 would be the primary instance, 1 the secondary, ...
        """
        num_inst = len(settings.dejavu_configs) - 1
        if inst_num > num_inst:
            logger.error('Instance number too high, maximum is ' + str(num_inst))
            return
        warnings.filterwarnings('ignore')
        dejavu_config = settings.dejavu_configs[inst_num]
        self.db = MudDatabase(**dejavu_config.get('database', {}))
        self.db.setup()
        self.djv = Dejavu(dejavu_config)
        self.inst_num = inst_num

    def build_collection(self):
        """
        Go through the collection song by song and add them to the
        dejavu database, if it is not already recognized.

        In any case, create an entry in the song_files database, pointing
        to the song_id in dejavu.songs

        """
        logger.info('Building collection')
        for song_f in self.list_new_files():
            logger.debug('Getting song id for ' + song_f)
            song_id = self.get_song_id(song_f)
            logger.debug('Adding "' + song_f + '" to collection with song_id ' + str(song_id))
            self.add_to_collection(song_f, song_id)

    def add_to_collection(self, song_file, song_id):
        """
        Add song_file to collection, with foreign key song_id

        song_file: string, absolute path to sound file
        song_id: int, foreign key to songs database

        """
        audio_file_tag = None
        try:
            audio_file = eyed3.load(song_file)
            audio_file_tag = audio_file.tag
        except IOError:
            return
        except eyed3.id3.tag.TagException:
            pass
        except Exception:
            pass
        tags = {}
        if audio_file_tag:
            tags['artist'] = audio_file.tag.artist
            tags['title'] = audio_file.tag.title
            tags['album'] = audio_file.tag.album
            for tag_name,tag_value in tags.iteritems():
                if tag_value:
                    tags[tag_name] = tag_value.strip().encode('utf-8')
                else:
                    tags[tag_name] = ''.encode('utf-8')
        else:
            logger.warning('File without valid mp3 tag, using filename as "title": ' + song_file)
            tags['artist'] = ''.encode('utf-8')
            tags['title'] = os.path.split(song_file)[1].replace('.mp3','').replace('.MP3','').decode('utf-8').encode('utf-8')
            tags['album'] = ''.encode('utf-8')
        artist = tags['artist']
        title = tags['title']
        album = tags['album']
        if song_id > 0:
            self.db.update_songfile(song_file, song_id, artist, title, album)
        else:
            self.db.update_error_on_songfile(song_file, artist, title, album, error_code=song_id)

    def list_new_files(self):
        """
        Return a list of filenames from the database that are not yet fingerprinted.
        """
        logger.debug('Getting not yet fingerprinted song files')
        for filepath in self.db.select_new_files():
            yield filepath['file_path']

    def get_song_id(self, song_file):
        """
        Return song_id of song_file, fingerprint first if nessessary.

        song_file: string, absolute path to sound file
        """
        song = None
        try:
            logger.debug('Fingerprinting ' + song_file)
            self.djv.fingerprint_file(song_file)
            logger.debug('Recognizing ' + song_file)
            song = self.djv.recognize(FileRecognizer, song_file)
        except pydub.exceptions.CouldntDecodeError:
            logger.error('CouldntDecodeError raised for ' + song_file)
            return ERROR_CODES['CouldntDecodeError']
        if song:
            logger.debug('Successfully recognized ' + song_file + ' with song_id ' + str(song['song_id']))
            return song['song_id']
        else:
            logger.error('SongObjectIsNone raised for ' + song_file)
            return ERROR_CODES['SongObjectIsNone']

    def scan_files(self):
        """Scan for music files and add them to the database."""
        if self.inst_num != 0: 
            logger.error('File scanning not permitted for non-primary instance')
            return
        logger.info('Scanning music base dir for mp3 files')
        for root, sub_folders, files in os.walk(settings.music_base_dir):
            for filepath in files:
                if filepath.endswith(('.mp3', '.MP3')):
                    path = os.path.join(root, filepath)
                    self.add_song_file(path.decode('utf-8'))

    def add_song_file(self, song_file):
        """Add a song file to the database, if it not already exists."""
        try:
            self.db.insert_songfile(song_file.encode('utf-8'))
        except IntegrityError:
            pass

    def yield_duplicates(self):
        """
        Query the database for duplicates and yield lists of duplicate song files

        This is achived by going through all song_ids and then list
        all song_files that point to a certain song_id. Only
        return song_ids (together with the song_files) that have more
        then one song_file pointing to them.
        """
        for sid in self.db.select_song_ids():
            files = []
            for path in self.db.select_file_by_id(sid['song_id']):
                files.append(path)
            if len(files) > 1:
                logger.debug('Yielding duplicate song id ' + str(sid['song_id']))
                yield files

    def get_duplicates(self):
        """
        Query the database for duplicates.
        """
        logger.debug('Getting duplicates')
        duplicates = []
        for files in self.yield_duplicates():
            duplicates.append(files)
        return duplicates

    def print_duplicates(self):
        """ Print duplicates to std out """
        dups = self.get_duplicates()
        if not dups:
            print('No duplicates found')
            return
        for sfiles in dups:
            print('')
            for sound_file in sfiles:
                song_title = sound_file['song_title']
                if not song_title: song_title = 'NO TITLE'
                print(song_title + ' - ' + sound_file['file_path'])

    def get_dup_albums(self):
        """
        Get duplicate albums
        """
        logger.debug('Assembling duplicate Albums')
        # assemble files that reside in the same directory
        raw_albums = collections.defaultdict(list)
        for files in self.yield_duplicates():
            raw_albums[os.path.dirname(files[0]['file_path'])] += [
                os.path.dirname(f['file_path']) for f in files[1:]]
        # We only want to keep directories which share at least
        # min_dup_per_dir duplicate files. While this must not
        # nessessarly be an album, it is a strong indicator.
        min_dup_per_dir = 2
        albums = collections.defaultdict(list)
        for directory,dup_dirs in raw_albums.iteritems():
            occurence = collections.defaultdict(int)
            for dup in dup_dirs:
                occurence[dup] += 1
            for num_dups_per_dir in occurence.values():
                if num_dups_per_dir >= min_dup_per_dir:
                    albums[directory] = occurence.keys()
                    break
        return albums

    def print_dup_albums(self):
        """
        Print duplicate albums
        """
        dup_albums = self.get_dup_albums()
        if not dup_albums:
            print('No albums found')
            return
        for album,dup_albums in dup_albums.iteritems():
            print
            print(album)
            for dup_album in dup_albums:
                print('    ' + dup_album)

    def print_stats(self):
        """Print some statistics."""
        logger.debug('Getting statistics')
        # Progress
        num_files = self.db.select_num_files()
        num_fingerprinted = self.db.select_num_fingerprinted()
        print('PROGRESS: ' + str(num_fingerprinted) + ' of ' + str(num_files) + ' fingerprinted.')
        # Errors
        for error_key in ERROR_CODES.keys():
            num_errors = self.db.select_num_errors(error_key)
            print('ERRORS: ' + str(num_errors) + ' ' + error_key)
        # Duplicates
        dups = self.get_duplicates()
        print('DUPLICATES: ' + str(len(dups)) + ' duplicates found')

    def check_files(self):
        """
        Go through songfiles table and check if each file still exists on disk.
        """
        logger.info('Checking all songs in database still exists on disk.')
        for song_file in self.db.select_all_song_files():
            if not os.path.isfile(song_file['file_path']):
                logger.info('Deleting ' + song_file['file_path'] + ' from database.')
                self.db.delete_song_file(song_file['file_path'])

def fill_dupes(inst_num, queue):
    """
    Create a mud instance and fill queue with duplicates.
    
    inst_num: int, the number 
    """
    mud_inst = mud(inst_num)
    for files in mud_inst.yield_duplicates():
        queue.put(files)
    queue.put(None)

def pass_duplicates(args):
    """
    Pass possible duplicates from one instance to the next instance.

    args: cli args. args.fill_instance is the instance duplicates should be passed to
    """
    if args.fill_instance < 1: raise Exception('Instance number must be > 0')
    logger.info('Filling instance no ' + str(args.fill_instance) + ' with duplicate candidates')
    mud_inst = mud(args.fill_instance)
    queue = MPQueue()
    p = Process(target=fill_dupes, args=(args.fill_instance -1, queue))
    p.start()
    counter = 0
    while True:
        files = queue.get()
        if not files:
            break
        for song_file in files:
            mud_inst.add_song_file(song_file['file_path'].decode('utf-8'))
            counter += 1
    p.join()
    logger.info('Filled instace no ' + str(args.fill_instance) + ' with ' + str(counter) + ' possible duplicates')

#
# CLI
#

def logging_setup(args):
    """
    Do setup of logging infrastructure.
    
    args: cli args as returnded by argparse.ArgumentParser.parse_args()

    """
    # Logging
    for level in [args.log_level, args.verbosity_level]:
        if not LOG_LEVELS.get(level, None):
            print('\'' + level +  '\' is not a valid log ore verbosity level. Must be one of ' 
                + str(LOG_LEVELS.keys()) + '.')
            exit(0)
    # create file handler
    fh = logging.FileHandler(settings.log_file)
    fh.setLevel(LOG_LEVELS[args.log_level])
    # create console handler
    ch = logging.StreamHandler()
    ch.setLevel(LOG_LEVELS[args.verbosity_level])
    # create formatter and add it to the handlers
    ch_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh_formatter = ch_formatter
    ch.setFormatter(ch_formatter)
    fh.setFormatter(fh_formatter)
    # add the handlers to logger
    logger.addHandler(ch)
    logger.addHandler(fh)
    try:
        # this is probably not part of the public api
        eyed3.utils.log.log.handlers.pop()
        eyed3.utils.log.log.addHandler(ch)
        eyed3.utils.log.log.addHandler(fh)
    except AttributeError:
        logger.warning('eyed3 log messages might not follow the general logging behaviour.')

def parse_cli_args():
    """
    Parse cli args and return an object with the given args
    """
    parser = argparse.ArgumentParser(
        description='Check for duplicates in your music collection. mud will \
            find all duplicates, even if the file is encoded at a different \
            bitrate. And of course it won\'t be fooled by tags :)')
    parser.add_argument('-s', '--scan',
                        action='store_true',
                        help='Scan music directory for new files. Only permited for primary instance (see -i)')
    parser.add_argument('-b', '--build-collection',
                        action='store_true',
                        help='Go through collection and build database of \
                            audio fingerprints.')
    parser.add_argument('-p', '--print-dups',
                        action='store_true',
                        help='Print all duplicates found.')
    parser.add_argument('-a', '--print-dup-albums',
                        action='store_true',
                        help='Print all duplicate albums found.')
    parser.add_argument('-t', '--print-stats',
                        action='store_true',
                        help='Print some statistics and progress information.')
    parser.add_argument('-c', '--check',
                        action='store_true',
                        help='Check if files in database still exist on disk.')
    parser.add_argument('-i', '--instance-number',
                        type=int,
                        default=0,
                        help='Specify the instance number. Default is 0, which is considered the "primary" instance.')
    parser.add_argument('-f', '--fill-instance',
                        type=int,
                        default=0,
                        help='Specify the instance to fill with possible duplicates. Argument must >= 1, if < 1 nothing will happen.')
    parser.add_argument('-V', '--Version',
                        action='store_true',
                        help='Display version.')
    parser.add_argument('-l', '--log-level',
                        type=str,
                        default='warning',
                        help='Specify the log level. One of debug, info, warning, error, \
                            critical. Default is "warning".')
    parser.add_argument('-v', '--verbosity-level',
                        type=str,
                        default='info',
                        help='Specify the verbosity level. One of debug, info, warning, \
                            error, critical. Default is "info".')
    return parser.parse_args()
 
if __name__ == '__main__':
    args = parse_cli_args()
    logging_setup(args)
    if args.Version:
        print(VERSION)
        exit(0)
    if args.fill_instance > 0:
        pass_duplicates(args)
    mud_inst = mud(args.instance_number)
    if args.scan:
        mud_inst.scan_files()
    if args.build_collection:
        mud_inst.build_collection()
    if args.check:
        mud_inst.check_files()
    if args.print_dups:
        mud_inst.print_duplicates()
    if args.print_dup_albums:
        mud_inst.print_dup_albums()
    if args.print_stats:
        mud_inst.print_stats()
