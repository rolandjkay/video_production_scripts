#! /usr/bin/env python
"""Process timecode as audio tracks in video clips

This Python scripts calls is designed to work with video clips in which one
audio channel contains timecode as an audio track and the other the camera
audio. We strip out the timecode audio and use it to relabel the starting
timecode of the video clip. Finally, we remux the camera audio track with the
video track to yield a video clip with a mono audio track.

Optionally, if the --audio_tracks option is given, we will also work on the
audio tracks from the audio recorder. In a proper, "double" recording system,
the cameras will listen to their timecode input and match the first video frame
to a timecode frame boundary. However, DSLR camera just start recording at an
arbitrary moment. 

We can count the number of bits in the first partial frame of timecode data
that we capture, however. So, we know the time of the first frame with 
sub-frame precision, but we can only label the first video frame with an
integer frame count.

We can adjust the audio, however. If we know that the starting timecode on 
the video track is 1/2 a frame too early then, if we pad with 1/2 a frame's
worth of audio data at the beginning of the audio track, they will both
sync up exactly.

Of course, if we have multiple cameras then, in general, there is no way that
they can all be lined up with the audio. However, we will typically have
an A camera and a B camera, and it would probably make sense to synchronize 
the audio with the A camera. In dialogue scenes, we will almost always 
be using footage from one camera at a time, so we just have to make sure
that we use an audio track that it sync'd to that camera.

If you pass the --audio_tracks option, this script will write synchronized
versions of the given tracks for each video input. Alongside each remuxed
video file, you'll find a version of each audio track given that has been
padded to match the video. Then, just make sure you use the correct audio
track in your project and you should have sub-frame precision synchronisation.

Of course, there's an argument that this is unnecessary. We can only see
25 frames per second, so sub-frame sync errors should not be noticable.
Without padding the audio tracks, the best we can manage is 1/2 frame
precion; ~ 1/50 s. I'm pretty sure that that will look in sync to the viewer.
However, the offset relative to the reference audio track is noticable and
it's easier in post production if you can quickly check that the 
syncronisation is exact.

"""
from subprocess import call, run
import os, sys
import json
import collections
import argparse
import traceback

TimecodeData = collections.namedtuple("TimecodeData", "timecode,num_discarded_bits")

def extract_timecode_data(filename):
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
        return TimecodeData(ltc_reader_output['Start'],
                            ltc_reader_output['DiscardedBitsAtStart'])
    else:
        return None

def mux(video_filename, audio_filename, timecode, output_filename):
    """Mux a video-only file with an audio file and set starting timecode"""
    status = run(['ffmpeg', '-i', video_filename, 
                            '-i', audio_filename, 
                            '-c', 'copy', '-map', '0:0', '-map', '1:0', 
                            '-timecode', timecode, output_filename ])



##
## Main
##
parser = argparse.ArgumentParser(description="Remux video files containin timecode audio track")
parser.add_argument('video_tracks', 
                    metavar='video-track', 
                    nargs='+',
                    help="A list of video tracks to remux")
parser.add_argument('-a, --audio-track', 
                    dest='audio_recorder_tracks', 
                    action='append', 
                    default=[], 
                    required=False,
                    help="A list of audio recorder tracks that are to be padded to match video timecodes"
                    )

args = parser.parse_args()

video_filenames = args.video_tracks
audio_recorder_filenames = args.audio_recorder_tracks

if len(video_filenames) == 0:
    print("No input files given")

ClipFiles = collections.namedtuple("ClipFiles", "video_filename,input_path,left_channel_filename,right_channel_filename,out_path,tmp_path")

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
failed_video_filenames = []

for video_filename in video_filenames:
    # Parse filename to path / filename . extension
    path, filename = os.path.split(video_filename)
    name, extension = os.path.splitext(filename)
    video_filename_obj = Filename(path, name, extension)

    # Create temp and output directories..
    tmp_path = os.path.join(video_filename_obj.path, "tmp")
    try:
        os.mkdir(tmp_path)
    except FileExistsError:
        pass
    
    out_path = os.path.join(video_filename_obj.path, "out")
    try:
        os.mkdir(out_path)
    except FileExistsError:
        pass


    # Extract both audio channels
    #
    left_channel_filename = os.path.join(tmp_path, video_filename_obj.name + '-left.wav')
    right_channel_filename = os.path.join(tmp_path, video_filename_obj.name + '-right.wav')

    returncode = call(['ffmpeg', '-i', video_filename, 
                             '-vn',
                             '-map_channel', '0.1.0', left_channel_filename, 
                             '-map_channel', ' 0.1.1', right_channel_filename])
    
    if returncode != 0:
        failed_video_filenames.append(video_filename)
        continue

    clips.append(ClipFiles(video_filename_obj, path, left_channel_filename, right_channel_filename,out_path,tmp_path))


# Extract timecode and remux the audio + video
#
for clip in clips:
    timecode_datas = [ extract_timecode_data(clip.left_channel_filename), 
                       extract_timecode_data(clip.right_channel_filename) 
                  ]


    try:
        if not any(timecode_datas):
            raise SystemError("No timecodes found in file");
        elif all(timecode_datas):
            raise SystemError("No audio found in file");
        else:
            if timecode_datas[0].timecode:
                timecode_data = timecode_datas[0]
                audio_filename = clip.right_channel_filename
            else:
                timecode_data = timecode_datas[1]
                audio_filename = clip.left_channel_filename

            output_filename_stub =  "OUT_" + clip.video_filename.name 
            output_filename = os.path.join(clip.out_path, 
                                           output_filename_stub + clip.video_filename.extension)

            mux(clip.video_filename.fq_name, audio_filename, timecode_data.timecode, output_filename) 


            ##
            ## Trim audio files for this video
            ##
            MICROSECS_PER_FRAME = 1000000 / 25
            MICROSECS_PER_BIT = MICROSECS_PER_FRAME / 80
            us_to_pad = int(timecode_data.num_discarded_bits * MICROSECS_PER_BIT)
            for audio_recorder_filename_in in audio_recorder_filenames:
                audio_recorder_path, audio_recorder_name = os.path.split(audio_recorder_filename_in)

                audio_recorder_filename_out = os.path.join(
                                                  clip.tmp_path, 
                                                  output_filename_stub + "__" + audio_recorder_name)


                print(["pad_wav", 
                                   audio_recorder_filename_in, 
                                   audio_recorder_filename_out, 
                                   '--microseconds', str(us_to_pad) ])

                returncode = call(["pad_wav", 
                                   audio_recorder_filename_in, 
                                   audio_recorder_filename_out, 
                                   '--microseconds', str(us_to_pad) ])
                if returncode != 0:
                    print("ERROR: Failed to pad audio file %s for video %s" % (audio_recorder_filename_in, video_filename),
                           file = sys.stderr)


                ## Copy metadate (including timecode from origianl WAV file
                ##
                riff_merge_filename_out = os.path.join(clip.out_path, 
                                                       output_filename_stub + "__" + audio_recorder_name)
                print(["riff_merge", 
                                   audio_recorder_filename_in, 
                                   audio_recorder_filename_out, 
                                   riff_merge_filename_out,
                                   ])

                returncode = call(["riff_merge", 
                                   audio_recorder_filename_in, 
                                   audio_recorder_filename_out, 
                                   riff_merge_filename_out,
                                   ])
                if returncode != 0:
                    print("ERROR: Failed to pad audio file %s for video %s" % (audio_recorder_filename_in, video_filename),
                           file = sys.stderr)
                

    except Exception as e:  
        failed_video_filenames.append(clip.video_filename.fq_name)

        print("ERROR: ",  e, file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)


print()
if len(failed_video_filenames) == 0:
    print("All files processed successfully")
else:
    print("FAILED TO PROCESS THESE FILES: " + ",".join(failed_video_filenames))




