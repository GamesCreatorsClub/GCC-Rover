#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo ""
echo Uploading     vl53l0x
pyros $1 upload -s vl53l0x $DIR/vl53l0x_service.py -e $DIR/vl53l0xWrapper.py $DIR/vl53l0x_python.so $DIR/vl53l0xPython.py
echo Restarting    vl53l0x
pyros $1 restart   vl53l0x

echo ""
echo "Currently running processes:"
pyros $1 ps