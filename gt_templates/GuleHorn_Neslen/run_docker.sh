#!/bin/bash

ulimit -s unlimited
cd /data
# /opt/delft3d_latest/lnx64/bin/run_dflow2d3d_parallel.sh 4 --dockerparallel
# /opt/dimrset/bin/run_dflow2d3d_parallel.sh 4 --dockerparallel /data/config_d_hydro.xml
/opt/dimrset/bin/run_dflow2d3d.sh /data/config_d_hydro.xml
