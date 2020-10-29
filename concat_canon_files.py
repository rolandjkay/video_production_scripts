#! /usr/bin/env python
"""Concatenate video files together

"""
from subprocess import call, run
import os, sys, re, shutil
import json
import collections
import uuid

input_filenames = sys.argv[1:]
failed_filenames = []

if not input_filenames:
    exit()

# Parse first filename to path / filename . extension
path, filename = os.path.split(input_filenames[0])

# Write out a file containing sub-part names
list_filename = os.path.join(path, "___mylist_" + str(uuid.uuid4()) + ".txt")
with open(list_filename, "w") as list_file:
    for input_filename in input_filenames:
        print("file '%s'" % input_filename, file = list_file)

 # Call ffmpeg to concatenate files.
print(['ffmpeg', '-f', 'concat', 
                 '-safe', '0', 
                 '-i', list_filename, 
                 '-c', 'copy', os.path.join(path,"FULL_" + filename )])
returncode = call(['ffmpeg', '-f', 'concat', 
                             '-safe', '0', 
                             '-i', list_filename, 
                             '-c', 'copy', os.path.join(path, "FULL_" + filename)])

try:
    os.remove(list_filename)
except Exception:
    pass

if returncode != 0:
    print("ffmpeg failed.", file = sys.stderr);
else:
    print("ffmpeg succeeded.", file = sys.stderr);

    # Move sub-parts into sub-dirs
    #
    subparts_path = os.path.join(path, "canon_subparts")
    try:
        os.mkdir(subparts_path)
    except FileExistsError:
        pass

    for input_filename in input_filenames:
       try:
           shutil.move(os.path.join(path, input_filename), subparts_path)
       except Exception:
           pass


