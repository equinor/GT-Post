#!/bin/bash
    #
    # This script is an example for running Delft3D-FLOW
    # Adapt and use it for your own purpose
    #
    # adri.mourits@deltares.nl
    # 27 Dec 2010
    #
    #
    # This script starts a single-domain Delft3D-FLOW computation on Linux
    #


    #
    # Set the config file here
    #
argfile=config_d_hydro.xml
# core file size to unlimited
ulimit -c unlimited




    #
    # Set the directory containing delftflow.exe here
    #
export ARCH=lnx64
export D3D_HOME=../../bin
exedir=/opt/delft3d_gt_NetCDF4/lnx64/flow2d3d/bin/

    #
    # No adaptions needed below
    #

    # Set some (environment) parameters
export LD_LIBRARY_PATH=$exedir:$LD_LIBRARY_PATH

    # Run
    # Please do not put 'rm delft3d.log' due to unexpected behaviour
    # this line creates a new clean log file upon restart
echo '' >> delft3d.log
$exedir/d_hydro.exe $argfile
touch done
