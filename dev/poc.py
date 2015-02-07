#!/usr/bin/python
# just playing around with Dejavu

from dejavu import Dejavu
from dejavu.recognize import FileRecognizer

from settings import dejavu_config

djv = Dejavu(dejavu_config)

song_file = '/home/isaac/lucky_chops_renc/Lucky Chops/Lucky Chops/Lucky Chops - Lucky Chops - 01 Hey Soul Sister.mp3'
song = djv.recognize(FileRecognizer, song_file)

print song
# prints {'song_id': 7, 'song_name': 'Lucky Chops - Lucky Chops - 01 Hey Soul Sister', 'confidence': 804, 'offset_seconds': -0.09288, 'match_time': 1.8062059879302979, 'offset': -2L}
