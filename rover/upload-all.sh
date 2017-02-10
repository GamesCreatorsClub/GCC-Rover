#!/bin/bash

echo ""
echo Uploading pyroslib
pyros $1 upload pyroslib  pyroslib/pyroslib.py

echo ""
echo Uploading wheels
pyros $1 upload -s wheels       wheels-service.py
echo Restarting wheels
pyros $1 restart wheels

echo ""
echo Uploading shutdown
pyros $1 upload -s shutdown     shutdown-service.py
echo Restarting shutdown
pyros $1 restart shutdown

echo ""
echo Uploading lights
pyros $1 upload -s lights       lights-service.py
echo Restarting lights
pyros $1 restart lights

echo ""
echo Uploading gyro-sensor
pyros $1 upload -s gyro-sensor  gyro-sensor-service.py
echo Restarting gyro-sensor
pyros $1 restart gyro-sensor

echo ""
echo Uploading sonar-sensor
pyros $1 upload -s sonar-sensor sonar-sensor-service.py
echo Restarting sonar-sensor
pyros $1 restart sonar-sensor

echo ""
echo "Currently running processes:"
pyros $1 ps