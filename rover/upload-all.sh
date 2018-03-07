#!/bin/bash
if [ -z "$1" ]
  then
    echo "Argument missing: Please supply rover IP or alias"
else

echo ""
echo Uploading     pyroslib
pyros $1 upload    pyroslib  pyroslib/pyroslib.py

echo ""
echo Uploading     storagelib
pyros $1 upload    storagelib   storagelib/storagelib.py

echo ""
echo Uploading     wifi
pyros $1 upload -s wifi         wifi_service.py
echo Restarting    wifi
pyros $1 restart   wifi

echo ""
echo Uploading     storage
pyros $1 upload -s storage      storage_service.py
echo Restarting    storage
pyros $1 restart   storage

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
echo Uploading     jcontroller
pyros $1 upload -s jcontroller  jcontroller_service.py
echo Restarting    jcontroller
pyros $1 restart   jcontroller

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

# echo ""
# echo Uploading     camera
# pyros $1 upload -s camera       camera_service.py
# echo Restarting    camera
# pyros $1 restart   camera

# echo ""
# echo Uploading     gyrosensor
# pyros $1 upload -s gyrosensor  gyrosensor_l3g4200d_service.py
# echo Restarting    gyrosensor
# pyros $1 restart   gyrosensor

# echo ""
# echo Uploading     accelsensor
# pyros $1 upload -s accelsensor  accelsensor_adxl345_service.py
# echo Restarting    accelsensor
# pyros $1 restart   accelsensor

# echo ""
# echo Uploading     9dofsensor
# pyros $1 upload -s 9dofsensor  mpu9250_service.py
# echo Restarting    9dofsensor
# pyros $1 restart   9dofsensor

# echo ""
# echo Uploading     sonarsensor
# pyros $1 upload -s sonarsensor sonarsensor_service.py
# echo Restarting    sonarsensor
# pyros $1 restart   sonarsensor

# echo ""
# echo Uploading     vl53l0x
# pyros $1 upload -s vl53l0x vl53l0x/vl53l0x_service.py -e vl53l0x/vl53l0xWrapper.py vl53l0x/vl53l0x_python.so vl53l0x/vl53l0xPython.py
# echo Restarting    vl53l0x
# pyros $1 restart   vl53l0x

echo ""
echo Uploading     discovery
pyros $1 upload -s discovery      discovery_service.py
echo Restarting    discovery
pyros $1 restart   discovery

echo ""
echo "Currently running processes:"
pyros $1 ps

fi
