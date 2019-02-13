#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo ""
echo Uploading     telemetry
pyros $1 upload -s telemetry $DIR/telemetry_service.py -e $DIR/telemetry_logger.py $DIR/telemetry_server.py $DIR/telemetry_storage.py $DIR/telemetry_stream.py $DIR/telemetry_pyros_logger.py $DIR/__init__.py
echo Restarting    telemetry
pyros $1 restart   telemetry

echo ""
echo "Currently running processes:"
pyros $1 ps