#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

SERVICE="pyroslib"

if [[ ! -z "$2" ]]; then
    SERVICE="$2:$SERVICE"
fi

echo ""
echo Uploading        $SERVICE
pyros $1 upload       $SERVICE $DIR/pyroslib.py -e $DIR/logging.py $DIR/__init__.py
