import unittest
import os
import sys

path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if not path in sys.path:
    sys.path.insert(1, path)
del path


class testMud(unittest.TestCase):

    def setup(self):
        # set base dir, possibly overwriting value in settings
        self.music_base_dir = ''
        settings.music_base_dir = self.music_base_dir


    @unittest.skip('TODO: implement this')
    def test_scan_files(self):
        pass

    @unittest.skip('TODO: implement this')
    def test_add_song_file(self):
        pass
