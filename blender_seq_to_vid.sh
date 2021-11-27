#!/bin/bash


# -h --> high quality
# -l --> low quality
# -s --> starting frame
#
ARGS=$(getopt -a --options hls:r: --long "high,low,start:,rate:" -- "$@")
 
eval set -- "$ARGS"

start="1"
export_prores=""
export_h264=""
start_frame="1"
frame_rate="25"

while true; do
  case "$1" in
    -h|--high)
      export_prores="YES"
      echo "Exporting ProRes 4444"
      shift 2;;
    -l|--low)
      export_h264="YES"
      echo "Exporting H264"
      shift 2;;
    -s|--start)
      start_frame="$2"
      echo "Starting at frame: " $2
      shift 2;;
    -r|--rate)
      frame_rate="$2"
      echo "Using frame rate: " $2
      shift 2;;
    --)
      shift
      break;;
  esac
done

if [ -z "$1" ] ; then
  output_stub="test"
else
  output_stub="$1"
fi

# By default, export ProRes only
if [ -z "$export_prores$export_h264" ] ; then
  export_prores="YES"
fi

if [ "$export_h264" == "YES" ] ; then
   ffmpeg -r $frame_rate -f image2 -s 1920x1080 -start_number $start_frame -i $1%04d.png -vcodec libx264 -crf $frame_rate  -pix_fmt yuv420p $output_stub.mp4
fi

if [ "$export_prores" == "YES" ] ; then
  ffmpeg -r $frame_rate -f image2 -s 1920x1080 -start_number $start_frame -i $1%04d.png -vcodec prores_ks -pix_fmt yuva444p10le -profile:v 4444   $output_stub.mov
fi

