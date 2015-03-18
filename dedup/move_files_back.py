#!/usr/bin/python

# move all files with a certain ending

import os

#root_dir = '/volume1/music'
root_dir = '/home/mobaxterm/git/dedup/testdir'

#non_mp3_dir = '/volume1/music_nonmp3'
non_mp3_dir = '/home/mobaxterm/git/dedup/non_mp3s'

# swap dirs
tmpdir = root_dir
root_dir = non_mp3_dir
non_mp3_dir = tmpdir

wanted_endings = ['mp3', 'MP3', ]

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

def find_nonmp3_files():
    """
    Find directories which contain nonmp3 music files
    """
    found_files = []
    for root, sub_folders, files in os.walk(root_dir):
        for file in files:
            if '.' in file:
                ending = file.split('.')[-1]
            else:
                continue
            if ending in wanted_endings:
                #print root + '/' + file
                found_files.append(root + '/' + file)
    return found_files

def delete_empty_dirs(root_dir):
    """
    Delete empty directories recursivly

    root_dir: root_dir to clean of empty dirs

    """
    print 'Deleting empty directories ... actual deletion will be anounced'
    dirs_deleted = 1
    while dirs_deleted > 0:
        print 'Deleting one layer of empty directories'
        dirs_deleted = 0
        for root, sub_folders, files in os.walk(root_dir):
            try:
                if not os.listdir(root):
                    print 'Deleting empty directory ' + root
                    os.rmdir(root)
                    dirs_deleted += 1
            except OSError:
                print 'OSError'
                pass



non_mp3_dirs = find_nonmp3_files()
move_files(non_mp3_dirs)
delete_empty_dirs(root_dir)
