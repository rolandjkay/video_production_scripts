
if [ -z "$1" ] ; then
  output_stub="test"
else
  output_stub="$1"
fi

ffmpeg -r 25 -f image2 -s 1920x1080 -start_number 1 -i $1%04d.png -vcodec libx264 -crf 25  -pix_fmt yuv420p $output_stub.mp4

