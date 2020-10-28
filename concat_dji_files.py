#! /usr/bin/env python
"""Concatenate DJI osmo files together

This Python scripts calls is designed to work with video clips in which one audio channel contains
timecode as an audio track and the other the camera audio. We strip out the timecode audio and
use it to relabel the starting timecode of the video clip. Finally, we remux the camera audio
track with the video track to yield a video clip with a mono audio track.

"""
from subprocess import call, run
import os, sys, re, shutil
import json
import collections


input_filenames = sys.argv[1:]
failed_filenames = []

for input_filename in input_filenames:
    # Parse filename to path / filename . extension
    path, filename = os.path.split(input_filename)
    name, extension = os.path.splitext(filename)

    m = re.match("(DJI_[0-9]{4})(_([0-9]{3}))?", name)
    if not m:
        print("Skipping '%s'" % input_filename);
        failed_filenames.append(input_filename)
    else:
        stub = m.group(1)
        #subfile_index = int(m.group(3))

        # Map a filename to None, if it is not a subpart with stub 'stub'
        # Otherwise, map to the stub index.
        def name_to_subpart(filename):
            m = re.match(stub + "_([0-9]{3}).MP4", filename)
            if m:
                subfile_index = int(m.group(1))
                return subfile_index
            else:
                return None


        # Search for the last sub-file.
        available_sub_parts = set(filter(None, 
                                         [ name_to_subpart(candidate) 
                                           for candidate in os.listdir(path if path else ".")]))
        num_sub_parts = max(available_sub_parts) 

        wanted_sub_parts = set(range(1, max(available_sub_parts) + 1))

        # Check that no parts are missing. Obivously, we can only check for holes,
        # not parts missing at the end.
        if available_sub_parts != wanted_sub_parts:
            missing_sub_parts = wanted_sub_parts - available_sub_parts

            print(missing_sub_parts, wanted_sub_parts, available_sub_parts)

            print("Missing sub-parts " + ", ".join(missing_sub_parts) +
                  " for file " + os.path.join(path, stub + ".MP4"))
            continue

        # Write out a file containing sub-part names
        list_filename = os.path.join(path, "___mylist.txt")
        with open(list_filename, "w") as list_file:
            for sub_part_index in wanted_sub_parts:
                print("file '%s_%03d'.MP4" 
                         % (os.path.join(path, stub), sub_part_index),
                      file = list_file)

        # Call ffmpeg to concatenate files.
        print(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_filename, '-c', 'copy', os.path.join(path, stub + ".MP4")])
        returncode = call(['ffmpeg', '-f', 'concat',  
                                     '-safe', '0',
                                     '-i', list_filename,
                                     '-c', 'copy',
                                     os.path.join(path, stub + ".MP4")])

        try:
            os.remove(list_filename)
        except Exception:
            pass

        if returncode != 0:
            print("Failed to concatenate " + stub + ".MP4")
            failed_filenames.append(input_filename)
            continue

        # Move sub-parts into sub-dirs
        #
        subparts_path = os.path.join(path, "dji_subparts")
        try:
            os.mkdir(subparts_path)
        except FileExistsError:
            pass

        for sub_part_index in wanted_sub_parts:
            sub_part_filename = "%s_%03d.MP4" % (os.path.join(path, stub), sub_part_index)
            try:
                shutil.move(os.path.join(path, sub_part_filename), subparts_path)
            except Exception:
                pass


if failed_filenames:
    print()
    print("These files failed: ")
    for x in failed_filenames:
        print("   " + x)


