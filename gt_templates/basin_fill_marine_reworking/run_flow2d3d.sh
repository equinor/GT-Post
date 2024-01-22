#!/bin/bash
argfile=config_d_hydro.xml
mdwfile=wave.mdw
export ARCH=lnx64
export D3D_HOME=/opt/delft3d_gt_NetCDF4
exedir=/opt/delft3d_gt_NetCDF4/lnx64/flow2d3d/bin
waveexedir=/opt/delft3d_gt_NetCDF4/lnx64/wave/bin
swanexedir=/opt/delft3d_gt_NetCDF4/lnx64/swan/bin
swanbatdir=/opt/delft3d_gt_NetCDF4/lnx64/swan/scripts

export LD_LIBRARY_PATH=$exedir:$LD_LIBRARY_PATH
export PATH=$exedir:$PATH
# Please do not put 'rm delft3d.log' due to unexpected behaviour
# this line creates a new clean log file upon restart
echo '' >> delft3d.log
$exedir/d_hydro.exe $argfile &

export LD_LIBRARY_PATH=$swanbatdir:$swanexedir:$waveexedir:$LD_LIBRARY_PATH
export PATH=$swanbatdir:$PATH
$waveexedir/wave.exe $mdwfile 1

