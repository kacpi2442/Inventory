#!/bin/sh
# This is a simple script to launch both applications

cleanup() {
    echo "Cleaning up..."
    kill $(jobs -p) 2>/dev/null
}

trap cleanup EXIT

cd "$(dirname "$0")"
export FLASK_APP=inventory_flask.py
# Check if .env file exists and if it does, export the variables
if [ ! -f .env ]
then
    export $(cat .env | xargs)
fi
waitress-serve --port=5000 inventory_flask:app &
python telegram_inventory.py &
wait