#!/bin/bash

ulimit -s unlimited

/opt/delft3d_latest/lnx64/bin/run_dflow2d3d_parallel.sh 4 --dockerparallel
