#!/usr/bin/python

# deduplicate a directory of files
# Isaac Hailperin <isaac.hailperin@gmail.com >
# November 2014
# Changelog: 06-nov-2014: first version

import os
import sys
import hashlib

###
# SETTINGS - DEFAULTS
###
# wether to really move stuff or not
simulate = True
# wether we want verbose information
verbose = False
# the directory to check for duplicates
dir_with_dupes = '/tmp'
# the directory where the duplicates should be moved
dir_dupes_target = '/var/tmp'
###
# END SETTINGS
###

def print_help():
    """
    print help message

    """
    print """ dedup.py is a small file duplicator. It works on all sorts of files, 
but could choke on files which exceed or come close to the maximum amount
of memory available.

Usage: dedup.py [-n|--no-simulate] [-v|--verbose] [-h|--help]

Options:
    -n|--no-simulate       - do not simulate, really move files (simulate is default)
    -v|--verbose           - be verbose
    -h|--help              - display this message
    -d|--duplicates <dir>  - directory which is to be deduplified. Defaults to """ + dir_with_dupes + """
    -t|--target <dir>      - directory where duplicates are to be moved. Defaults to """ + dir_dupes_target 
    exit(0)

def iprint(text):
    """
    print the provided text if verbose=True
    """
    if verbose:
        print text

def get_recursive_file_list(root_dir):
    """
    Get a recursive listing of files and dirs in
    root_dir: string, the root dir to start the file listing
    """
    print "Getting recursive file list for " + root_dir
    file_list = []
    dir_list = []
    for root, sub_folders, files in os.walk(root_dir):
        for file in files:
            file_list.append(os.path.join(root,file))
        for dir in sub_folders:
            dir_list.append(root + '/' + dir)
    return (file_list, dir_list)

def get_duplicates(file_list):
    """
    Identify duplicates by calculating a checksum of all files in 

    file_list: list of filenames

    NOTE: this will cause memory problems for large files. There is a suggested solution for this:
    http://stackoverflow.com/questions/3431825/generating-a-md5-checksum-of-a-file
    but at least in mobaxterm, this yielded wrong checksums ...
    """
    print 'Checking files for duplicates'
    checksums = {}
    duplicates = []
    for file in file_list:
        try:
            checksum = hashlib.sha256(open(file, 'rb').read()).hexdigest()
        except IOError:
            print 'ERROR: could not calculate checksum for ' + file
            continue
        try:
            checksums[checksum].append(file)
            duplicates.append(file)
        except KeyError:
            checksums[checksum] = [file]
    if verbose or simulate:
        all_dup_files = [ dups for dups in checksums.values() if len(dups) > 1 ]
        for dups in all_dup_files:
            for file in dups:
                print file
            print
    return duplicates

def create_path(path):
    """
    Check if path exists, if not, create dirs

    path: string, full path to file

    """
    dir  = os.path.dirname(path)
    if not os.path.exists(dir):
        if not simulate:
            os.makedirs(dir)

def move_files(file_list):
    """
    Move given files to a new dir, rebuilding the dir tree as in the original

    file_list: list of filenames

    """
    if simulate:
        return
    for old_path in file_list:
        new_path = dir_dupes_target + old_path.split(dir_with_dupes)[1]
        create_path(new_path)
        iprint('Moving ' + old_path + ' to ' + new_path)
        os.rename(old_path, new_path)

def delete_empty_dirs(dir_list):
    """
    Delete empty directories. Also take care of dirs that got emptied by this procedure.

    dir_list: list of directories

    """
    if simulate:
        return
    iprint('Deleting empty directories ... actual deletion will be anounced')
    dirs_deleted = 1
    while dirs_deleted > 0:
        iprint('Deleting one layer of empty directories')
        dirs_deleted = 0
        for dir in dir_list:
            try:
                if not os.listdir(dir):
                    iprint('Deleting empty directory ' + dir)
                    os.rmdir(dir)
                    dirs_deleted += 1
            except OSError:
                pass

if __name__ == "__main__":
    # parse args
    i = -1
    for arg in sys.argv:
        i += 1
        if arg == "-n" or arg == "--no-simulate":
            simulate = False
        if arg == '-v' or arg == '--verbose':
            verbose = True
        if arg == '-h' or arg == '--help':
            print_help()
        if arg == '-d' or arg == '--duplicates':
            try:
                dir_with_dupes = sys.argv[i + 1]
            except IndexError:
                dir_with_dupes = ''
            if dir_with_dupes.startswith('-') or dir_with_dupes == '':
                print '-d|--duplicates needs an argument'
                exit(0)
        if arg == '-t' or arg == '--target':
            try:
                dir_dupes_target = sys.argv[i + 1]
            except IndexError:
                dir_dupes_target = ''
            if dir_dupes_target.startswith('-') or dir_dupes_target == '':
                print '-t|--target needs an argument'
                exit(0)
    # actual dedup
    (recursive_file_list, dir_list) = get_recursive_file_list(dir_with_dupes)
    duplicates = get_duplicates(recursive_file_list)
    move_files(duplicates)
    delete_empty_dirs(dir_list)


