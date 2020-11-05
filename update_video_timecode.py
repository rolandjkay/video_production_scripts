#! /usr/bin/env python
"""Update video timecode to match audio

If we've been unable to record a timecode audio track then we need to manually sync the audio
tracks with the video. This can be done in Premiere Pro, but it doesn't work well when we
start cutting the clips up to make the scene; we end up having to manually sync every line
of dialogue.

It's much better to sync the audio track once and for all, for each clip, before editing starts
and then update the timecodes in the video files, so that Premiere Pro cannot mess things up.

To use this script,...
  1) go through each video clip and find the corresponding audio track.
  2) identify a matching frame in the audio and video tracks; this is your reference frame.
  3) Pass the video and audio track timecodes that correspond to the ref frame 
     to this script
  4) This script will output a video file with the timecode updated to match the audio

update_video_timecode.py -a hh:mm:ss:ff -v hh:mm:ss:ff 1S3A8029.MOV


"""
import collections
import argparse
import re
from subprocess import call, run

FRAMES_PER_HOUR = 3600*25
FRAMES_PER_MINUTE = 60*25
FRAMES_PER_SECOND = 25

_Timecode = collections.namedtuple("Timecode", "h,m,s,f")
class Timecode(_Timecode):
    def __str__(self):
        return str(self.h) + ":" + str(self.m) + ":" + str(self.s) + ":" + str(self.f)

    @classmethod
    def from_str(cls, string):
        m = re.match("([0-9]{2}):([0-9]{2}):([0-9]{2}):([0-9]{2})", string)
        if not m:
            raise ValueError("Invalid timecode string: " + string)

        return Timecode(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))



def tc_to_frame_count(tc):
    return tc.h*FRAMES_PER_HOUR + tc.m*FRAMES_PER_MINUTE + tc.s*FRAMES_PER_SECOND + tc.f

def frame_count_to_tc(frame_count):
    hours, remainder = int(frame_count / FRAMES_PER_HOUR) % 24, frame_count % FRAMES_PER_HOUR
    minutes, remainder = int(remainder / FRAMES_PER_MINUTE), frame_count % FRAMES_PER_MINUTE
    seconds, remainder = int(remainder / FRAMES_PER_SECOND), frame_count % FRAMES_PER_SECOND

    return Timecode(hours, minutes, seconds, remainder)

def calc_tc_diff(a, b):
    """Calculate a - b as a frame count"""
    a_frame_count = tc_to_frame_count(a)
    b_frame_count = tc_to_frame_count(b)

    return a_frame_count - b_frame_count

def apply_tc_diff(tc, diff):
    frame_count = tc_to_frame_count(tc)
    frame_count += diff
    return frame_count_to_tc(frame_count)

def read_video_start_timecode(filename):
    result = run([ 'ffprobe', 
                   '-show_entries', 'stream_tags=timecode',
                   '-of', 'default=noprint_wrappers=1',
                   filename,
                   '-v', 'error'], capture_output = True)

    first_line = result.stdout.decode("utf-8").split("\n")[0]
    m = re.match("TAG:timecode=([0-9]{2}):([0-9]{2}):([0-9]{2}):([0-9]{2})", first_line)
    return Timecode(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))

##
## Parse command line args
##
parser = argparse.ArgumentParser(description="Video clip to process")
parser.add_argument('video_filename', 
                    metavar='video filename', 
                    help="The video filename to work on")
parser.add_argument('-a, --audio-ref-timecode', 
                    dest='audio_ref_timecode', 
                    action='store', 
                    required=True,
                    help="The audio timecode of the reference frame"
                    )
parser.add_argument('-v, --video-ref-timecode', 
                    dest='video_ref_timecode', 
                    action='store', 
                    required=True,
                    help="The video timecode of the reference frame"
                    )

args = parser.parse_args()

video_filename = args.video_filename
output_filename = "TC_" + video_filename
video_ref_timecode = Timecode.from_str(args.video_ref_timecode) 
audio_ref_timecode = Timecode.from_str(args.audio_ref_timecode)

##
## Do the work
##

video_start_timecode = read_video_start_timecode(video_filename)

# Use reference timecode to calculate difference between video 
# and audio timecodes.
diff = calc_tc_diff(audio_ref_timecode, video_ref_timecode)

# Apply difference to video start time code
new_video_start_timecode = apply_tc_diff(video_start_timecode, diff)

status = run(['ffmpeg', '-i', video_filename, 
                        '-c', 'copy', 
                        '-timecode', str(new_video_start_timecode), output_filename ])
