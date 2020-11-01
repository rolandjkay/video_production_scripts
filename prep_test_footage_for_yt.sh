# Process all MOV files into a single low resolution file for upload to YouTube.
#

rm -f __yt_clips.txt
rm -f __description.txt
timestamp="0.0"

WIDTH=480

mkdir -p __tiny
for T in *.MOV ; do
  echo Processing $T ...
  ffmpeg -i $T -vf scale=$WIDTH:-2,setsar=1:1,drawtext="fontfile=/path/to/font.ttf: \
                             text='$T': fontcolor=white: fontsize=24: box=1:
                             boxcolor=black@0.5: \
                             boxborderw=5: x=0: y=0" -codec:a copy __tiny/textt-$T
  echo file \'__tiny/textt-$T\' >> __yt_clips.txt
  duration=`ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $T`
  timestamp=`echo $timestamp + $duration | bc`
  echo -e 'import time\nprint(time.strftime("%H:%M:%S", time.gmtime(' $timestamp')), "' $T '")'  | python >> __description.txt

done

ffmpeg -f concat -safe 0 -i __yt_clips.txt -c copy upload.mov
