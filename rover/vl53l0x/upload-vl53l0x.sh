#!/bin/bash

echo ""
echo Uploading     vl53l0x
pyros $1 upload -s vl53l0x vl53l0x_service.py -e vl53l0xapi.py vl53l0x_python.so vl53l0x_full_impl.py
echo Restarting    vl53l0x
pyros $1 restart   vl53l0x

echo ""
echo "Currently running processes:"
pyros $1 ps