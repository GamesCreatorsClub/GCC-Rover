#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

$DIR/../pyroslib/upload-pyroslib.sh $1 wheels
$DIR/../storagelib/upload-storagelib.sh $1 wheels

echo ""
echo Uploading        storage
pyros $1 upload -s -r storage      $DIR/storage_service.py
echo Restarting       storage
pyros $1 restart      storage

echo ""
echo Uploading        discovery
pyros $1 upload -s -r discovery    $DIR/discovery_service.py
echo Restarting       discovery
pyros $1 restart      discovery

echo ""
echo Uploading        wifi
pyros $1 upload -s -r wifi         $DIR/wifi_service.py
echo Restarting       wifi
pyros $1 restart      wifi

echo ""
echo Uploading        power
pyros $1 upload -s -r power        $DIR/type-c/power_service.py
echo Restarting       power
pyros $1 restart      power

echo ""
echo Uploading        drive
pyros $1 upload -s -r drive        $DIR/type-c/drive_service.py
echo Restarting       drive
pyros $1 restart      drive

echo ""
echo Uploading        shutdown
pyros $1 upload -s -r shutdown     $DIR/type-c/shutdown_service.py
echo Restarting       shutdown
pyros $1 restart      shutdown

$DIR/telemetry/upload-telemetry.sh $1
$DIR/vl53l1x/upload-vl53l1x.sh $1

echo "Uploading all for wheels:"

$DIR/upload-telemetry-wheels.sh $1
$DIR//upload-wheels.sh $1
$DIR/pyroslib/upload-pyroslib.sh $1

echo ""
echo "Currently running processes:"
pyros $1 ps