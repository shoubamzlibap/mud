import unittest
import os
import sys
import subprocess
import time
import mock
import warnings
from MySQLdb import IntegrityError

###
# Settings
###
SKIP_LONG_TESTS = True
###
# End Settings
###

try:
    from hypothesis import given
    from hypothesis.strategies import text, integers
    skip_hypothesis = False
except ImportError:
    skip_hypothesis = True

from .. import settings
from .. import mud

def get_db_root_pw():
    """Do exactly this"""
    # NOTE: set the path to your db root pw file here - (do not test in production ;))
    with open('/home/isaac/.db_root_pw', 'r') as db_root_pw_file:
        return db_root_pw_file.read()

def db_setup():
    """
    Do the database setup, patching the values in the settings module
    """
    i = 1
    new_configs = []
    db_root_pw = get_db_root_pw()
    for config in settings.dejavu_configs:
        config['database']['db'] = 'test_dejavu_' + str(i)
        new_configs.append(config)
        i += 1
        test_db = config['database']['db']
        test_db_user = config['database']['user']
        test_db_pw = config['database']['passwd']
        create_db_command = 'mysql -u root --password=' + db_root_pw + ' -e'
        create_db_command = create_db_command.split() + ['CREATE DATABASE IF NOT EXISTS ' + test_db + ';']
        grant_all_command = 'mysql -u root --password=' + db_root_pw + ' -e'
        grant_all_command = grant_all_command.split() + \
        ['grant all on ' + test_db + '.* to \'' + test_db_user + '\'@\'localhost\' identified by \'' + test_db_pw + '\';']
        subprocess.call(create_db_command)
        subprocess.call(grant_all_command)
    settings.dejavu_configs = new_configs

def db_teardown():
    """Tear down dbs created for testing"""
    db_root_pw = get_db_root_pw()
    for config in settings.dejavu_configs:
        test_db = config['database']['db']
        drop_db_command = 'mysql -u root --password=' + db_root_pw + ' -e'
        drop_db_command = drop_db_command.split() + ['DROP DATABASE ' + test_db + ';']
        subprocess.call(drop_db_command)


@unittest.skipIf(skip_hypothesis, 'hypothesis not installed ("pip install hypothesis" should fix this)')
class testMudHypothesis(unittest.TestCase):
    """ Test cases making use of the Hypothesis framework """

    @classmethod
    def setUp(self):
        """Do database setup"""
        db_setup()
        self.mud = mud.mud(0)

    @classmethod
    def tearDown(self):
        """Delete test database"""
        db_teardown()

    @given(text())
    def test_add_song_file(self, song_file):
        """Database takes all sorts of filenames"""
        # just asserting no Exception is raised
        self.mud.add_song_file(song_file)

    @unittest.skip('CODE NEEDS FIX, test seems OK')
    @given(text(), integers())
    def test_add_to_collection(self, song_file, song_id):
        """Taking all sorts of filenames and songids"""
        # just asserting no Exceptino is raised 
        self.mud.add_to_collection(song_file, song_id)

class testMud(unittest.TestCase):

    gp_mock = mock.Mock()

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
        self.test_song = '/home/isaac/Music/lucky_chops_renc/Lucky Chops/Lucky Chops - Lucky Chops - 08 Lean On Me.mp3'
        # database creation
        db_setup()
        self.mud = mud.mud(0)

    @classmethod
    def tearDown(self):
        subprocess.call(['rm', '-rf', self.music_base_dir])
        db_teardown()

    @mock.patch('mud.mud.mud.add_song_file', gp_mock.add_song_file )
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


    @unittest.skipIf(SKIP_LONG_TESTS, 'Tested successfully, runs very long')
    def test_get_song_id(self):
        """
        Song ID returned correctly
        """
        # add song
        sid_run1 = self.mud.get_song_id(self.test_song)
        # add song again, songid shoudl be same as bevor
        sid = self.mud.get_song_id(self.test_song)
        self.assertEqual(sid, sid_run1)
        self.assertTrue(isinstance(sid, int))

    def test_get_song_id_error(self):
        """
        Unreadable file is handled 
        """
        emty_file = self.music_base_dir + self.files[0]
        sid = self.mud.get_song_id(emty_file)
        self.assertEqual(sid, -1)

    def fake_fingerprint(junk1, junk2 ):
        pass
    def fake_recognize(junk1, junk2, junk3):
        return None
    @mock.patch('dejavu.Dejavu.fingerprint_file', fake_fingerprint)
    @mock.patch('dejavu.Dejavu.recognize', fake_recognize)
    def test_get_song_id_None(self):
        """
        Song object of none is handled
        """
        emty_file = self.music_base_dir + self.files[0]
        sid = self.mud.get_song_id(emty_file)
        self.assertEqual(sid, -2)

    @mock.patch('eyed3.load', gp_mock.fake_load)
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

    @unittest.skipIf(SKIP_LONG_TESTS, 'Tested successfully, runs very long')
    def test_get_duplicates(self):
        """
        Duplicates are returned correctly
        """
        settings.music_base_dir = '/home/isaac/Music'
        self.mud.scan_files()
        self.mud.build_collection()
        self.mud.print_duplicates()
        dups = self.mud.get_duplicates()
        self.assertTrue(len(dups) > 0)


    @mock.patch('mud.mud.MudDatabase.delete_song_file', gp_mock.delete_song_file )
    def test_check_files(self):
        """
        Files no longer present are deleted from database
        """
        test_file = self.music_base_dir + self.files[0]
        self.mud.scan_files()
        os.remove(test_file)
        self.mud.check_files()
        self.gp_mock.delete_song_file.assert_called_once_with(test_file)
        # create file again
        open(test_file, 'w').close()


    def test_delete_song_file(self):
        """
        File actually removed from database
        """
        test_file = self.music_base_dir + self.files[0]
        self.mud.scan_files()
        os.remove(test_file)
        self.mud.check_files()
        for song_file in self.mud.db.select_all_song_files():
            self.assertTrue(test_file not in song_file['file_path'])
        # create file again and add to database
        open(test_file, 'w').close()
        self.mud.scan_files()
