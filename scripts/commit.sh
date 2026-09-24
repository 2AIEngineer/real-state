#!/bin/bash

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
MESSAGE=${1:-$TIMESTAMP}

git add .

git commit -m "$MESSAGE"
if [ $? -ne 0 ]; then
    echo "[ERROR] Commit failed."
    exit 1
fi

git push
if [ $? -ne 0 ]; then
    echo "[ERROR] Push failed."
    exit 1
fi

echo "[OK] Push done successfully."