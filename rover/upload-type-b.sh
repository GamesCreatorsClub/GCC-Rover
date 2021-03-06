#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

$DIR/pyroslib/upload-pyroslib.sh $1

echo ""
echo Uploading     storagelib
pyros $1 upload    storagelib   $DIR/storagelib/storagelib.py

echo ""
echo Uploading     storage
pyros $1 upload -s storage      $DIR/storage_service.py
echo Restarting    storage
pyros $1 restart   storage

echo ""
echo Uploading     discovery
pyros $1 upload -s discovery    $DIR/discovery_service.py
echo Restarting    discovery
pyros $1 restart   discovery

echo ""
echo Uploading     wifi
pyros $1 upload -s wifi         $DIR/wifi_service.py
echo Restarting    wifi
pyros $1 restart   wifi

echo ""
echo Uploading     wheels
pyros $1 upload -s wheels       $DIR/type-ab/wheels_service.py
echo Restarting    wheels
pyros $1 restart   wheels

echo ""
echo Uploading     drive
pyros $1 upload -s drive        $DIR/type-ab/drive_service.py
echo Restarting    drive
pyros $1 restart   drive

echo ""
echo Uploading     shutdown
pyros $1 upload -s shutdown     $DIR/shutdown_service.py
echo Restarting    shutdown
pyros $1 restart   shutdown

echo ""
echo Uploading     lights
pyros $1 upload -s lights       $DIR/lights_service.py
echo Restarting    lights
pyros $1 restart   lights

echo ""
echo Uploading     camera
pyros $1 upload -s camera       $DIR/camera_service.py
echo Restarting    camera
pyros $1 restart   camera

echo ""
echo Uploading     9dofsensor
pyros $1 upload -s 9dofsensor  $DIR/mpu9250_service.py
echo Restarting    9dofsensor
pyros $1 restart   9dofsensor

echo ""
echo Uploading     sonarsensor
pyros $1 upload -s sonarsensor $DIR/sonarsensor_service.py
echo Restarting    sonarsensor
pyros $1 stop      sonarsensor

echo ""
echo Uploading     vl53l0x
pyros $1 upload -s vl53l0x $DIR/vl53l0x_service.py
echo Restarting    vl53l0x
pyros $1 restart   vl53l0x

echo ""
echo "Currently running processes:"
pyros $1 ps