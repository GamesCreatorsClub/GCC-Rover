#!/bin/bash

echo ""
echo Uploading        wheels:vl53l1x
pyros $1 upload -s -r wheels:vl53l1x vl53l1x_service.py -e GCC_VL53L1X.py example.py gcc_vl53l1x.cpython-35m-arm-linux-gnueabihf.so __init__.py

echo ""
echo "Currently running processes:"
pyros $1 ps