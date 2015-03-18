#!/usr/bin/python

# move all dirs containing files with a certain ending

import os

root_dir = '/volume1/music'

non_mp3_dir = '/volume1/music_nonmp3'

wanted_endings = ['wma', 'wav', 'ogg', 'aif', 'ape', 'mpc', 'm4a', 'flac', 'm4p', 'wmv', ]

def create_path(path):
    """
    Check if path exists, if not, create dirs

    path: string, full path to file

    """
    dir  = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)

def move_files(file_list):
    """
    Move given files to a new dir, rebuilding the dir tree as in the original

    file_list: list of filenames

    """
    for old_path in file_list:
        new_path = non_mp3_dir + old_path.split(root_dir)[1]
        create_path(new_path)
        print 'Moving ' + old_path + ' to ' + new_path
        os.rename(old_path, new_path)

def find_nonmp3_dirs():
    """
    Find directories which contain nonmp3 music files
    """
    found_dirs = []
    for root, sub_folders, files in os.walk(root_dir):
        for file in files:
            if '.' in file:
                ending = file.split('.')[-1]
            else:
                continue
            if ending in wanted_endings and root not in found_dirs:
                print root
                found_dirs.append(root)
    return found_dirs


non_mp3_dirs = find_nonmp3_dirs()
move_files(non_mp3_dirs)
