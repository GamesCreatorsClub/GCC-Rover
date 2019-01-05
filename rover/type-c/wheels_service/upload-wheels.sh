#!/bin/bash

echo ""
echo Uploading     wheels
pyros $1 upload -s wheels wheels_service.py -e nRF2401
echo Restarting    wheels
pyros $1 restart   wheels

echo ""
echo "Currently running processes:"
pyros $1 ps