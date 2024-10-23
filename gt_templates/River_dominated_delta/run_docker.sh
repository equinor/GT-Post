#!/bin/bash

ulimit -s unlimited
cd /data
/opt/dimrset/bin/run_dflow2d3d_parallel_dwaves.sh 4 --dockerparallel -w /data/wave.mdw /data/config_d_hydro.xml
