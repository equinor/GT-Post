#!/bin/bash
while true
do
    if find /data/input/ -name 'trim-*.nc' -mmin -10 | grep -q .
    then
        pixi run python "$@"
    fi
    sleep 10m
done
