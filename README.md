# Python Portfolio - ArcPy/GIS Solar Site Profile Tool

GIS (ArcPy/ArcGIS) focused Python script to compile key variables for one or many polygons that are important for determining site suitability for solar development. 

author: evan fedorko, evanjfedorko@gmail.com
date: 3/2021

This script takes in a polygon GIS feature class of 1 to X features and uses a bunch of
pre-generated GIS data describing various things that are important to determining
solar site suitability and spits out a table of all those things for each site, one line per
input site. Those variables include: distance to transmission lines of various capacities,
slope on the site, and landuse on the site.

this must be run with ArcGIS python 2 build system from ESRI as installed with ArcGIS 10.8. 
Compiling sample data for this that gets under the 25 mb limit proved to be a pain...
so I didn't do it. 
