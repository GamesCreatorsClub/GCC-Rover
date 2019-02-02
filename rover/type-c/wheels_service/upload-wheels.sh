#!/bin/bash

echo ""
echo Uploading     wheels:wheels
pyros $1 upload -s wheels:wheels wheels_service.py -e nRF2401
echo Restarting    wheels:wheels
pyros $1 restart   wheels:wheels

echo ""
echo "Currently running processes:"
pyros $1 ps