#!/bin/bash

echo ""
echo Uploading     pyroslib
pyros $1 upload    pyroslib  pyroslib/pyroslib.py

echo ""
echo Uploading     wheels
pyros $1 upload -s wheels       wheels_service.py
echo Restarting    wheels
pyros $1 restart   wheels

echo ""
echo Uploading     drive
pyros $1 upload -s drive        drive_service.py
echo Restarting    drive
pyros $1 restart   drive

echo ""
echo Uploading     shutdown
pyros $1 upload -s shutdown     shutdown_service.py
echo Restarting    shutdown
pyros $1 restart   shutdown

echo ""
echo Uploading     lights
pyros $1 upload -s lights       lights_service.py
echo Restarting    lights
pyros $1 restart   lights

echo ""
echo Uploading     camera
pyros $1 upload -s camera       camera_service.py
echo Restarting    camera
pyros $1 restart   camera

echo ""
echo Uploading     gyrosensor
pyros $1 upload -s gyrosensor  gyrosensor_service.py
echo Restarting    gyrosensor
pyros $1 restart   gyrosensor

echo ""
echo Uploading     accelsensor
pyros $1 upload -s accelsensor  accelsensor_service.py
echo Restarting    accelsensor
pyros $1 restart   accelsensor

echo ""
echo Uploading     sonarsensor
pyros $1 upload -s sonarsensor sonarsensor_service.py
echo Restarting    sonarsensor
pyros $1 restart   sonarsensor

echo ""
echo "Currently running processes:"
pyros $1 ps