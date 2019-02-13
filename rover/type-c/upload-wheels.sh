#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo "Uploading all for wheels:"


$DIR/../pyroslib/upload-pyroslib.sh $1 "wheels"
$DIR/../storagelib/upload-storagelib.sh $1 "wheels"

echo ""
echo Uploading     wheels:shutdown
pyros $1 upload -s wheels:shutdown     $DIR/../shutdown_service_fast.py
echo Restarting    wheels:shutdown
pyros $1 restart   wheels:shutdown

$DIR/../telemetry/upload-telemetry-wheels.sh $1
$DIR/wheels_service/upload-wheels.sh $1

echo ""
echo "Currently running processes:"
pyros $1 ps