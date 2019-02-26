#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo ""
echo Uploading        wheels:wheels
pyros $1 upload -r -s wheels:wheels $DIR/wheels_service.py -e $DIR/nRF2401
echo Restarting       wheels:wheels
pyros $1 restart      wheels:wheels
