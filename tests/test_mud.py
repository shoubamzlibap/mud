import unittest
import os
import sys
import subprocess
import time
import mock
import warnings
from MySQLdb import IntegrityError

path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if not path in sys.path:
    sys.path.insert(1, path)
del path

import settings

class testMud(unittest.TestCase):

    @classmethod
    def setUp(self):
        # set base dir, possibly overwriting value in settings
        self.music_base_dir = '/tmp/mud'
        settings.music_base_dir = self.music_base_dir
        # clean up first
        subprocess.call(['rm', '-rf', self.music_base_dir])
        # create some dummy files
        self.dirs = [ '/foo/bar', '/foo/baz']
        self.files = [ '/foo/file1.mp3', '/foo/bar/file2.mp3', '/foo/baz/file3.mp3', '/foo/baz/file3.mp4']
        for d in self.dirs:
            os.makedirs(self.music_base_dir + d)
        for f in self.files:
            open(self.music_base_dir + f, 'w').close()
        # test song
        self.test_song = '/home/isaac/lucky_chops_renc/Lucky Chops/Lucky Chops - Lucky Chops - 08 Lean On Me.mp3'
        # database creation
        self.test_db = 'mudtest'
        settings.dejavu_config['database']['db'] = self.test_db
        test_db_user = settings.dejavu_config['database']['user']
        test_db_pw = settings.dejavu_config['database']['passwd']
        # NOTE: set the path to your db root pw file here - (do not test in production ;))
        with open('/home/isaac/.db_root_pw', 'r') as db_root_pw_file:
            self.db_root_pw = db_root_pw_file.read()
        create_db_command = 'mysql -u root --password=' + self.db_root_pw + ' -e'
        create_db_command = create_db_command.split() + ['CREATE DATABASE IF NOT EXISTS ' + self.test_db + ';']
        grant_all_command = 'mysql -u root --password=' + self.db_root_pw + ' -e'
        grant_all_command = grant_all_command.split() + \
        ['grant all on ' + self.test_db + '.* to \'' + test_db_user + '\'@\'localhost\' identified by \'' + test_db_pw + '\';']
        subprocess.call(create_db_command)
        subprocess.call(grant_all_command)
        # get mud
        import mud
        self.mud = mud
        # create database object for later usage
        warnings.filterwarnings('ignore')
        import mud
        self.db = mud.MudDatabase(**settings.dejavu_config.get('database',{}))
        self.db.setup()

    #@classmethod
    def tearDown(self):
        subprocess.call(['rm', '-rf', self.music_base_dir])
        drop_db_command = 'mysql -u root --password=' + self.db_root_pw + ' -e'
        drop_db_command = drop_db_command.split() + ['DROP DATABASE ' + self.test_db + ';']
        subprocess.call(drop_db_command)

    gp_mock = mock.Mock()
    @mock.patch('mud.add_song_file', gp_mock.add_song_file )
    def test_scan_files(self):
        """
        Files in testdir scanned correctly
        """
        self.mud.scan_files()
        for f in [g for g in self.files if g.endswith('.mp3') ]:
            self.gp_mock.add_song_file.assert_any_call(self.music_base_dir + f)

    def test_insertfiles(self):
        """
        Files are inserted and retrieved correctly from db
        """
        # insert file - expecting no Exceptions
        for f in self.files:
            self.mud.add_song_file(f)
        # insert file twice (should not add file twice, checked below)
        for f in self.files:
            self.mud.add_song_file(f)
        # select new files
        new_files = []
        for f in self.mud.list_new_files():
            new_files.append(f)
        self.assertListEqual(sorted(new_files), sorted(self.files))


    @unittest.skip('Tested successfully, runs very long')
    def test_get_song_id(self):
        """
        Song ID returned correctly
        """
        # add song, songid shoudl be 1
        sid = self.mud.get_song_id(self.test_song)
        self.assertEqual(sid, 1)
        # add song again, songid shoudl be 1
        sid = self.mud.get_song_id(self.test_song)
        self.assertEqual(sid, 1)

    my_mock = mock.Mock()
    @mock.patch('eyed3.load', my_mock.fake_load)
    def test_update_songfile(self):
        """
        Song ID updated correctly
        """
        test_file = self.files[0]
        song_id = 23
        self.mud.add_song_file(test_file)
        # just asserting no Exception raised
        with self.assertRaises(IntegrityError):
            self.mud.add_to_collection(test_file, song_id )

    @unittest.skip('Tested successfully, runs very long')
    def test_get_duplicates(self):
        """
        Duplicates are returned correctly
        """
        settings.music_base_dir = '/home/isaac'
        self.mud.scan_files()
        self.mud.build_collection()
        dups = self.mud.get_duplicates()
        print dups

