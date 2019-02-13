#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo ""
echo Uploading        vl53l1x
pyros $1 upload -s -r vl53l1x $DIR/vl53l1x_service.py -e $DIR/GCC_VL53L1X.py $DIR/range.py $DIR/gcc_vl53l1x.cpython-35m-arm-linux-gnueabihf.so $DIR/__init__.py

echo ""
echo "Currently running processes:"
pyros $1 ps