#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo ""
echo Uploading     screen
pyros $1 upload -s screen $DIR/screen_service.py -e $DIR/roverscreen.py $DIR/garuda.ttf $DIR/gccui $DIR/graphics $DIR/images
echo Restarting    screen
pyros $1 restart   screen
