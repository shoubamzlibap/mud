#!/usr/bin/python

# get all file endings (once) for all files in root_dir

import os

root_dir = '/home/mobaxterm'

file_endings = []
for root, sub_folders, files in os.walk(root_dir):
    for file in files:
        if '.' in file:
            ending = file.split('.')[-1]
        else:
            continue
        if not ending in file_endings:
            file_endings.append(ending)
            print "*." + ending

#print file_endings

