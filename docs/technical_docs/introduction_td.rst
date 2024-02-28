1 - Preprocessing
#################

Preprocessing in d3d-geotool is the process of creating and adjusting all the required 
Delft3D input files for running a model. It requires 'templates' with basic D3D input 
files as a basis. These templates dictate some parameters that require expert knowlegde, 
the choice of equations that govern the hydronamic and morphological processes and 
the overall bathymetric layout. Preprocessing consists of the following steps:

1. Creating the 'input.ini' file with user-adjustable parameters and the chosen template
2. Running the preprocessing code based on the input.ini file. This process entails:
   
 * Copying the default template files to the the folder where you want to run your model from.
 * Parsing user-defined parameters from the input.ini and removing any obsolete files (e.g. files associated with other sediment compositions).
 * Generating bathymetries (a.dep and wave.dep) based on user-given 'basin slope'.
 * Generating the subsidence (.sdu) file based on user-given subsidence rates.
 * Replacing parameters in various input files by values given in the input.ini file.
  
Upon finishing this process, the newly created Delft3D input folder is ready for use.

1.1 - Templates for model building
**********************************
Currently there are four templates to choose from:

River Dominated delta  
   *Template for a generic river-dominated delta system. Has a straight coastline and a 
   v-shaped initial river valley that is 100 cells (5 km) long. Uses Engelund-Hansen  
   sediment transport equation.*

GuleHorn_Neslen
   *Template for Gule Horn and Neslen formations and comparable deltaic systems. Has a 
   straight coastline and a simple initial river valley that is 100 cells (5 km) long. 
   The fluvial input location shifts overtime to enforce meandering in the fluvial 
   domain. Uses Engelund-Hansen sediment transport equation.*

.. figure:: ../images/River_dominated_delta_GuleHorn_Neslen.jpg
  :width: 600

  Illustration of river dominated and GuleHorn_Neslen templates

Roda
   *Template for the Roda formation and comparable deltaic systems. Has a straight, but
   funnel-shaped coastline and a simple initial river valley that is 100 cells (5 km) 
   long. Uses Van Rijn sediment transport equation.*

.. figure:: ../images/Roda.jpg
  :width: 600

  Illustration of the Roda template

Sobrarbe
    *Template for the Sobrarbe formation and comparable deltaic systems. Has a straight, 
    and short 20 cell (1 km) river valley. The river valley has four inflow points
    for channels that are separated by cone-shaped non-eordable obstacles. Simulates a
    wide braided floodplain entering a sedimentary basin. Uses Van Rijn sediment 
    transport equation.*

.. figure:: ../images/Sobrarbe.jpg
  :width: 600

  Illustration of the Sobrarbe template

1.2 - The input.ini file
************************
The input.ini file is where you can edit all user-adjustable model parameters. The
preprocessing script needs this file as input alongside a folder location to write the
Delft3D input files to. Below is a description of editable parameters

.. csv-table:: input.ini overview
   :header: Parameter,Description
   :delim: |
   :file: inputini_overview.csv

2 - Postprocessing
##################
After running a model the postprocessing modules of d3d-geotool can be used to generate
additional data from the completed models. The following results can be generated from a 
completed Delft3D model run:

* Sediment (distribution) properties: d-values, sorting, porosity and permeability.
* Preserved deposits and age of these deposits.
* Subenvironments: Delta top, Delta front and Prodelta
* Channel data: channel network, channel skeleton, channel width, channel depth
* Architectural elements
* Additional statistics per architectural element: volume percentage of total delta volume, D50 distribution, average sorting and average sand fraction.

2.1 - Sediment properties
*************************
The following parameters are used to calculate sediment properties:

* D50 per input sediment class (derived from sed-file or calculated, see below)
* Dry bed density per sediment class (derived from sed-file)
* Mass fluxes per sediment class ('DMSEDCUM' in trim.nc file)

.. note:: 

   Sediment classes are defined by the 'composition' parameter in the input.ini

D50 per input sediment type is directly taken from the sed-file if the sediment class 
type is sand. In the case of mud, the settling velocity is used to derive a D50-value,
using:

.. math:: 
   D_{50} = \sqrt{18 * \mu * \eta / g / (\rho_p - \rho_f)}

where :math:`{\mu}` is the settling velocity, :math:`{\eta}` is dynamic viscosity, 
:math:`{\rho_p}` is the specific density of the material, :math:`{\rho_f}` is the 
density of water and :math:`{g}` is the acceleration due to gravity.

At a given time and location, positive mass fluxes per sediment class directly determine 
the composition of sediment preserved during the given output timestep. Combined with 
the dry bed density of each sediment class, the mass distribution of deposited sediment 
is first converted to volume fractions. Sediment volume fraction data is then used to 
compute a cumulative sediment distribution function (CDF), from which other parameters 
such as median grain size (D50), porosity and permeability will be derived. 

The calculation of the CFD can best be described by an example: A ‘coarse-sand’ D3D-GT 
model has the following proportions of six sediment classes, with associated median 
grain size for that class, at a single location in the model output:

.. csv-table:: 
   :header: Sediment class,Grain size :math:`{\theta}` (:math:`{\mu}`m),Example volume fractions
   :delim: |
   :file: example_vfractions.csv

These fractions are used to compute the CDF by linear interpolation within a phi-scale 
range of [coarsest – 0.5] to [finest + 0.5]. Hence for the above example, the 
distribution is calculated between -0.5 and 4.84, corresponding to grain sizes of 1414 
to 36 μm. Since the grain sizes in the above table represent median grain size of the 
sediment class, the interpolation points were are inbetween sediment classes. Thus, 
the following points are used for interpolation of the given example:

.. csv-table:: 
   :header: Grain size :math:`{\phi}`,Quantile
   :delim: |
   :file: example_interpolation_pts.csv

Linear interpolation between these points result in the CDF shown in the Figure below.
The D50 of the sediment mixture within that cell then follows from the CDF, as it 
corresponds to the 0.5 quantile. In the example case the corresponding median grain size 
is 1.6 on the phi-scale, which translates to 330 μm. Other d-values can be obtained from
this interpolated CDF.

.. figure:: ../images/example_cdf.jpg
  :width: 600

  Example of linear interpolation between sediment class mass fraction values to produce 
  a cumulative distribution function at each location in the simulated sediment body. 
  Note that due to use of the phi scale the coarsest grain sizes occur on the left and 
  the finest on the right of the graph.


2.2 - Preservation and deposition age
*************************************
Blabla

2.3 - Subenvironment classification
***********************************
Blabla

2.4 - Channel classification
****************************
Blabla

2.5 - Architectural element classification
******************************************

3 - Data export
###############
All (postprocessing) data can be exported to a single netCDF file or a specified 
timestep can be exported to a VTK file for 3D viewing.

4 - Built-in visualizations
###########################
d3d-geotool provides various built-in visualization options 