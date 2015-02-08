import unittest
import os
import sys
import subprocess
import time
import mock

path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if not path in sys.path:
    sys.path.insert(1, path)
del path

import settings
import mud

class testMud(unittest.TestCase):

    @classmethod
    def setUp(self):
        # general purpose mock object
        #self.gp_mock = mock.Mock()
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

    #@classmethod
    def tearDown(self):
        subprocess.call(['rm', '-rf', self.music_base_dir])

    gp_mock = mock.Mock()
    @mock.patch('mud.add_song_file', gp_mock.add_song_file )
    def test_scan_files(self):
        """
        Files in testdir scanned correctly
        """
        mud.scan_files()
        for f in [g for g in self.files if g.endswith('.mp3') ]:
            self.gp_mock.add_song_file.assert_any_call(self.music_base_dir + f)

    @unittest.skip('TODO: implement this')
    def test_add_song_file(self):
        pass
