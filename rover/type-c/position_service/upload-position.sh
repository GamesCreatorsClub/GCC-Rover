#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo ""
echo Uploading        position
pyros $1 upload -s -r -e python3.7 position $DIR/position_service.py -e $DIR/rover_1 $DIR/rover_1_35
echo Restarting       position
pyros $1 restart      position
