#!/bin/bash

echo ""
echo Uploading     screen
pyros $1 upload -s screen screen_service.py -e roverscreen.py garuda.ttf wheel.png gccui
echo Restarting    screen
pyros $1 restart   screen

echo ""
echo "Currently running processes:"
pyros $1 ps