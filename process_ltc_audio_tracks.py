#! /usr/bin/env python
"""Process timecode as audio tracks in video clips

This Python scripts calls is designed to work with video clips in which one audio channel contains
timecode as an audio track and the other the camera audio. We strip out the timecode audio and
use it to relabel the starting timecode of the video clip. Finally, we remux the camera audio
track with the video track to yield a video clip with a mono audio track.

"""
from subprocess import call, run
import os, sys
import json
import collections

def extract_timecode(filename):
    """Call ltcdump to get the starting timecode of the given audio file"""

    # Convert filename to Windows path

    result = run(['ltcdump', filename, "-j"], capture_output = True) 

    try:
        ltc_reader_output = json.loads(result.stdout)
    except json.decoder.JSONDecodeError as e:
        print("Error parsing JSON output from ltcdump:")
        print()
        print(e.doc)
        print()
        print(e.msg)
        print("at line: %d, column %d" % (e.lineno, e.colno))
        print()
        raise


    if ltc_reader_output['ResultCode'] == 200:
        print("Found timecode %s in file %s" % (ltc_reader_output['Start'], filename))
        return ltc_reader_output['Start']
    else:
        return None

def mux(video_filename, audio_filename, timecode, output_filename):
    """Mux a video-only file with an audio file and set starting timecode"""
    status = run(['ffmpeg', '-i', video_filename, 
                            '-i', audio_filename, 
                            '-c', 'copy', '-map', '0:0', '-map', '1:0', 
                            '-timecode', timecode, output_filename ])




input_filenames = sys.argv[1:]

if len(input_filenames) == 0:
    print("No input files given")

ClipFiles = collections.namedtuple("ClipFiles", "input_filename,input_path,left_channel_filename,right_channel_filename,out_path")

class Filename:
    def __init__(self, path, name, extension):
        self._path = path
        self._name = name
        self._extension = extension

    @property
    def path(self):
        return self._path

    @property
    def name(self):
        return self._name

    @property
    def extension(self):
        return self._extension

    @property
    def fq_name(self):
        return os.path.join(self._path, self._name + self._extension)

clips = []
failed_input_filenames = []

for input_filename in input_filenames:
    # Parse filename to path / filename . extension
    path, filename = os.path.split(input_filename)
    name, extension = os.path.splitext(filename)
    input_filename_obj = Filename(path, name, extension)

    # Create temp and output directories..
    tmp_path = os.path.join(input_filename_obj.path, "tmp")
    try:
        os.mkdir(tmp_path)
    except FileExistsError:
        pass
    
    out_path = os.path.join(input_filename_obj.path, "out")
    try:
        os.mkdir(out_path)
    except FileExistsError:
        pass


    # Extract both audio channels
    #
    left_channel_filename = os.path.join(tmp_path, input_filename_obj.name + '-left.wav')
    right_channel_filename = os.path.join(tmp_path, input_filename_obj.name + '-right.wav')

    returncode = call(['ffmpeg', '-i', input_filename, 
                             '-vn',
                             '-map_channel', '0.1.0', left_channel_filename, 
                             '-map_channel', ' 0.1.1', right_channel_filename])
    
    if returncode != 0:
        failed_input_filenames.append(input_filename)
        continue

    clips.append(ClipFiles(input_filename_obj, path, left_channel_filename, right_channel_filename,out_path))


# Extract timecode and remux the audio + video
#
for clip in clips:
    timecodes = [ extract_timecode(clip.left_channel_filename), 
                  extract_timecode(clip.right_channel_filename) 
                ]


    try:
        if not any(timecodes):
            raise SystemError("No timecodes found in file");
        elif all(timecodes):
            raise SystemError("No audio found in file");
        else:
            if timecodes[0]:
                timecode = timecodes[0]
                audio_filename = clip.right_channel_filename
            else:
                timecode = timecodes[1]
                audio_filename = clip.left_channel_filename

            output_filename = os.path.join(clip.out_path, "OUT_" + clip.input_filename.name + clip.input_filename.extension)

            mux(clip.input_filename.fq_name, audio_filename, timecode, output_filename) 

    except Exception as e:  
        failed_input_filenames.append(clip.input_filename.fq_name)

        print(e)


print()
if len(failed_input_filenames) == 0:
    print("All files processed successfully")
else:
    print("FAILED TO PROCESS THESE FILES: " + ",".join(failed_input_filenames))




