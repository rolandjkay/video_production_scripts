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
    return;

# Write out a file containing sub-part names
list_filename = os.path.join(path, "___mylist_" + uuid.uuid4() + ".txt")
with open(list_filename, "w") as list_file:
    for input_filename in input_filenames:
        print("file '%s'" % input_filename, file = list_file)

# Parse first filename to path / filename . extension
path, filename = os.path.split(input_filename[0])

 # Call ffmpeg to concatenate files.
print(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_filename, '-c', 'copy', os.path.join(path, stub + ".MP4")])
returncode = call(['ffmpeg', '-f', 'concat', 
                             '-safe', '0', 
                             '-i', list_filename, 
                             '-c', 'copy', os.path.join(path, "FULL_" + filename)])

try:
    os.remove(list_filename)
except Exception:
    pass

if returncode != 0:
    printf("ffmpeg failed.", file = std.stderr);


