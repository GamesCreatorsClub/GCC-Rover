#!/bin/bash

echo ""
echo Uploading     telemetry
pyros $1 upload -s telemetry telemetry_service.py -e telemetry_logger.py telemetry_server.py telemetry_storage.py telemetry_stream.py telemetry_pyros_logger.py __init__.py
echo Restarting    telemetry
pyros $1 restart   telemetry

echo ""
echo "Currently running processes:"
pyros $1 ps