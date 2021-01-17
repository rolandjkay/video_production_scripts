#!/bin/sh
#
# Compress a video a lot and split into <5 min subvideos so that it can be sent over WeChat

# Recompress at 0.5Mbps video and 64kpbs audio to target.mp4
ffmpeg -i $1 -c:v libx264 -b:v 0.5M -c:a aac -b:a 64k target.mp4

# Split target.mp4 -> target0.mp4 target1.mp4 etc.
ffmpeg -i target.mp4 -f segment -segment_time 280 -vcodec copy -reset_timestamps 1 target%d.mp4

