#!/bin/bash

echo ""
echo Uploading     pyroslib
pyros $1 upload    pyroslib  pyroslib/pyroslib.py

echo ""
echo Uploading     storagelib
pyros $1 upload    storagelib   storagelib/storagelib.py

echo ""
echo Uploading     storage
pyros $1 upload -s storage      storage_service.py
echo Restarting    storage
pyros $1 restart   storage

echo ""
echo Uploading     discovery
pyros $1 upload -s discovery    discovery_service.py
echo Restarting    discovery
pyros $1 restart   discovery

echo ""
echo Uploading     wifi
pyros $1 upload -s wifi         wifi_service.py
echo Restarting    wifi
pyros $1 restart   wifi

echo ""
echo Uploading     drive
pyros $1 upload -s drive        type-c/drive_service.py
echo Restarting    drive
pyros $1 restart   drive

echo ""
echo Uploading     shutdown
pyros $1 upload -s shutdown     shutdown_service.py
echo Restarting    shutdown
pyros $1 restart   shutdown

cd telemetry

./upload-telemetry.sh $1
./upload-telemetry-wheels.sh $1

cd wheels_service
./upload-wheels.sh $1

cd ../..

echo ""
echo "Currently running processes:"
pyros $1 ps