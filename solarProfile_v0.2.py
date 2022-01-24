"""
author: evan fedorko, evanjfedorko@gmail.com
date: 3/2021

This script takes in a polygon GIS feature class of 1 to X features and uses a bunch of
pre-generated GIS data describing various things that are important to determining
solar site suitability and spits out a table of all those things for each site, one line per
input site. Those variables include: distance to transmission lines of various capacities,
slope on the site, and landuse on the site.

this must be run with ArcGIS python 2 build system from ESRI as installed with ArcGIS 10.8
"""

import arcpy
from arcpy import env
from arcpy.sa import *
import pandas as pan
arcpy.CheckOutExtension("spatial")

# environments and paths
ws = "D:\\workspace\\solarSiteAnalysis"
arcpy.env.workspace = ws
arcpy.env.overwriteOutput = "True"

# OUPUT
outputTables = ws + "\\Python\\Output"
targetStyle = pan.read_csv(ws + "\\Python\\SiteProfileOutputTemplateTwo.csv")
tempDF = pan.DataFrame(targetStyle)
temp = ws + "\\Python\\temp.gdb"

# Processing variables
eData = "D:\\workspace\\gis_data\\DEM_1to3"
stateElev = eData + "DEM_Mosaic_WV_Statewide_1to3m_UTM17_p2020.tif"
regionSlope = eData + "\\StatewideElev.gdb"
counties = ws + "\\RESOURCES\\county_24k_utm83_NEW.shp"
owner = ''
county = ''
OriginalOID = 0

regionList = {
	eData + "\\WV_central_region_northernPiece.shp": regionSlope + "\\CentNorthSlope",
	eData + "\\WV_central_region_southernPiece.shp": regionSlope + "\\CentSouthSlope",
	eData + "\\WV_east_region.shp": regionSlope + "\\EastSlope",
	eData + "\\WV_south_region_northern.shp": regionSlope + "\\SouthNorthSlope",
	eData + "\\WV_south_region_southern.shp": regionSlope + "\\SouthSouthSlope"
}

currentRegion = temp + "\\currentRegion"
lulc = ws + "\\RESOURCES\\WV_LULC_NAIP.tif"
lulcGood = ws + "\\RESOURCES\\WV_LULC_NAIP_2016_reclassedToGoodForSolar_correct.tif"
floodMath = ws + "\\RESOURCES\\DFIRM_FloodZones_AAE_AsNoDataAndOne.tif"
minePermits = ws + "\\RESOURCES\\mining_reclamation_permit_boundary.shp"

# Processing storage and other references
slopeAreasAllLULC = {
	"0-5 percent": 0,
	"5-10 percent": 0,
	"10-15 percent": 0,
	"15-20 percent": 0,
	"Over 20 percent": 0
}

slopeAreasGoodLULC = {
	"0-5 percent": 0,
	"5-10 percent": 0,
	"10-15 percent": 0,
	"15-20 percent": 0,
	"Over 20 percent": 0
}

FieldNameToSlopeCat = {
	"0-5 percent": "VALUE_1",
	"5-10 percent": "VALUE_2",
	"10-15 percent": "VALUE_3",
	"15-20 percent": "VALUE_4",
	"Over 20 percent": "VALUE_5"
}

reclassSlope = [[0, 5, 1], [5, 10, 2], [10, 15, 3], [15, 20, 4], [20, 25, 5], [25, ]]

transmission = {
	ws + "\\RESOURCES\\TransmissionLinesWV.gdb\\TransDist_Under100KV": "Under 100 kV",
	ws + "\\RESOURCES\\TransmissionLinesWV.gdb\\TransDist_UnknownKV": "Unknown kV",
	ws + "\\RESOURCES\\TransmissionLinesWV.gdb\\TransDist_735kvAndUp": "735kV and Up",
	ws + "\\RESOURCES\\TransmissionLinesWV.gdb\\TransDist_500kv": "500 kV",
	ws + "\\RESOURCES\\TransmissionLinesWV.gdb\\TransDist_345kv_2": "345 kV",
	ws + "\\RESOURCES\\TransmissionLinesWV.gdb\\TransDist_100to161kv": "100 to 161 kV"
}

transmissionDistances = {
	"Unknown kV": 0,
	"Under 100 kV": 0,
	"100 to 161 kV": 0,
	"345 kV": 0,
	"500 kV": 0,
	"735kV and Up": 0
}

whereClause = ""


# would be good to have an acutal name field in future inputs rather than just a number
def analysis():
	outputDF = pan.DataFrame(data=None, columns=tempDF.columns)
	outputDF.set_index('Index')

	# cursor for parcel data
	# with arcpy.da.SearchCursor(testFeature, ['OID@','SHAPE@','OWNER1']) as cursor:
	with arcpy.da.SearchCursor(testFeature, ['OID@', 'SHAPE@']) as cursor:
		featureNum = 0
		arcpy.MakeFeatureLayer_management(counties, "counties_lyr")
		# this loop identifies which sub-region of elevation data we will need to work from
		for feature in cursor:
			OriginalOID = feature[0]
			print("Working on OBJECTID: " + str(OriginalOID))
			location = ""
			loops = 0
			area = 0
			owner = 'NA'
			# owner for parcel data
			# owner = feature[3]
			area += feature[1].getArea("GEODESIC", "ACRES")

			# get county name; ideally we would be using a center point but we don't have the license to run that tool
			arcpy.SelectLayerByLocation_management("counties_lyr", "intersect", feature[1], "", "NEW_SELECTION")
			arcpy.CopyFeatures_management("counties_lyr", "D:\\workspace\\solarSiteAnalysis\\Python\\temp.gdb\\tempCounty")
			returnRows_meta = arcpy.SearchCursor("D:\\workspace\\solarSiteAnalysis\\Python\\temp.gdb\\tempCounty", whereClause)
			# value of county name field passed to variable to be passed to table later
			# looping through all returns like this is resulting in errors
			for row_meta in returnRows_meta:
				county = row_meta.NAME
			for region, slope in regionList.items():
				# feature[1] refers to the 'SHAPE@' element of the SearchCursor which is a geometry object
				arcpy.SpatialJoin_analysis(region, feature[1], currentRegion, 'JOIN_ONE_TO_ONE', 'KEEP_COMMON', 'COMPLETELY_CONTAINS')
				# this stuff can probably be replaced with an arcpy.Describe object to save processing time; FIDset I think it is called
				# making a layer is expensive, I assume
				arcpy.MakeFeatureLayer_management(currentRegion, "currentRegion_lyr")
				testval = arcpy.GetCount_management("currentRegion_lyr")
				loops += 1
				if int(str(testval)) != 0:
					location = slope
				if location != "":
					break
				elif location == "" and loops == (len(regionList)):
					print("start a loop from clipped data")

			# GIS analysis starts here. write all site specific GIS data to jobOutput+"\\name_"+str(featureNum)
			# be sure to write TEMP things to temp+"\\name"; these should always be written over

			arcpy.CopyFeatures_management(feature[1], jobOutput + "\\AOI_" + str(featureNum))  # copy AOI feature to output database
			arcpy.Clip_management(slope, "#", temp + "\\siteSlope", feature[1], "#", "ClippingGeometry", "NO_MAINTAIN_EXTENT")  # clip slope
			siteSlopeFPRemoved = arcpy.sa.Times(temp + "\\siteSlope", floodMath)  # remove flood plains from slope data
			siteSlopeFPRemoved.save(temp + "\\siteSlopeClean")
			# reclass slope
			arcpy.gp.Reclassify_sa(temp + "\\siteSlopeClean", "VALUE", "0 5 1;5 10 2;10 15 3;15 20 4;20 25 5;25 500000 9", jobOutput + "\\siteSlopeReclass_" + str(featureNum), "DATA")
			# tab area of slope
			arcpy.gp.TabulateArea_sa(feature[1], "OID", jobOutput + "\\siteSlopeReclass_" + str(featureNum), "VALUE", jobOutput + "\\slopeClassArea_allLULC_" + str(featureNum))
			for key, value in slopeAreasAllLULC.items():
				try:
					fieldName = FieldNameToSlopeCat[key]
					with arcpy.da.SearchCursor(jobOutput + "\\slopeClassArea_allLULC_" + str(featureNum), fieldName) as cursor2:
						for row in cursor2:
							slopeAreasAllLULC[key] = row[0] * 0.0002471052
				except Exception:
					slopeAreasAllLULC[key] = -9999
			try:
				if cursor2:
					del cursor2
			except Exception:
				continue

			# cross tab area of slope by good LULC (good = 1, bad = 0)
			# this gives a table of two sets of slope acres per class, one set for good areas, one for bad areas.
			# zones (0,1 field name "VALUE") per row, slope class per column (field names "VALUE_1" through 5 and 9 for nodata
			arcpy.gp.TabulateArea_sa(lulcGood, "VALUE", jobOutput + "\\siteSlopeReclass_" + str(featureNum), "VALUE", jobOutput + "\\slopeClassArea_goodLULC_" + str(featureNum))
			for key, value in slopeAreasGoodLULC.items():
				try:
					fieldName = FieldNameToSlopeCat[key]
					with arcpy.da.SearchCursor(jobOutput + "\\slopeClassArea_goodLULC_" + str(featureNum), fieldName, "VALUE = 1") as cursor3:
						for row in cursor3:
							slopeAreasGoodLULC[key] = row[0] * 0.0002471052
				except Exception:
					slopeAreasGoodLULC[key] = -9999
			try:
				if cursor3:
					del cursor3
			except Exception:
				continue

			# find distance to nearest transmission lines by size (including all)
			# transmission lines dict variable is called transmission
			for line, category in transmission.items():
				try:
					arcpy.gp.ZonalStatisticsAsTable(feature[1], "OID", line, temp + "\\TransLineTemp", "#", "MINIMUM")
					read = arcpy.SearchCursor(temp + "\\TransLineTemp", whereClause)
					for line in read:
						transmissionDistances[category] = line.MIN * 0.0006213712
				except Exception:
					print("Zonal stats as table failed")
					for category, value in transmissionDistances.items():
						transmissionDistances[category] = -9999
					break
			try:
				if read:
					del read
			except Exception:
				continue

			# check for mine permits (yes/no for now)
			arcpy.MakeFeatureLayer_management(jobOutput + "\\AOI_" + str(featureNum), "feature_lyr")
			arcpy.SelectLayerByLocation_management("feature_lyr", "INTERSECT", minePermits)
			arcpy.CopyFeatures_management("feature_lyr", temp + "\\forCount")
			mineCount = arcpy.GetCount_management(temp + "\\forCount")
			mineTest = int(mineCount.getOutput(0))
			if mineTest > 0:
				mineIntersect = "yes"
			else:
				mineIntersect = "no"

			# MAYBE ADD ADDRESS POINT THING HERE - count address points

			# count parcels, create list of owners? TO BE ADDED LATER BECAUSE MAKING A LAYER OF PARCELS IS WAY TOO DEMANDING
			# there must be a processing extent setting somewhere that will make this processing more sensible

			# write single row to dict
			newRow = {
				"Index": featureNum,
				"SiteGroup": jobName,
				"SourceFID": OriginalOID,
				"Area": area,
				"FlatGoodLULC": slopeAreasGoodLULC.get("0-5 percent") + slopeAreasGoodLULC.get("5-10 percent"),
				"UnknownkV": transmissionDistances.get("Unknown kV"),
				"Under100kV": transmissionDistances.get("Under 100 kV"),
				"100to161kV": transmissionDistances.get("100 to 161 kV"),
				"345kV": transmissionDistances.get("345 kV"),
				"500kV": transmissionDistances.get("500 kV"),
				"735kV": transmissionDistances.get("735kV and Up"),
				"AllSlope0to5": slopeAreasAllLULC.get("0-5 percent"),
				"AllSlope5to10": slopeAreasAllLULC.get("5-10 percent"),
				"AllSlope10to15": slopeAreasAllLULC.get("10-15 percent"),
				"AllSlope15to20": slopeAreasAllLULC.get("15-20 percent"),
				"AllSlopeOver20": slopeAreasAllLULC.get("Over 20 percent"),
				"GoodLULC0to5": slopeAreasGoodLULC.get("0-5 percent"),
				"GoodLULC5to10": slopeAreasGoodLULC.get("5-10 percent"),
				"GoodLULC10to15": slopeAreasGoodLULC.get("10-15 percent"),
				"GoodLULC15to20": slopeAreasGoodLULC.get("15-20 percent"),
				"GoodLULCOver20": slopeAreasGoodLULC.get("Over 20 percent"),
				"MinePermits": mineIntersect,
				"Owner": owner,
				"County": county}
			outputDF = outputDF.append(newRow, ignore_index="True")  # append dict to dataframe as new row
			print("feature number " + str(featureNum) + " complete")
			featureNum += 1
			writeToCsv(outputDF)


# write output to csv
def writeToCsv(targetDF):
	targetDF.to_csv(csvFile)


# main program

"""
inputs that change are jobName and testFeature
for parcels it is also importat to make changes to lines 95/96 and lines 107/108
these can become GetParameterAsText(0) and GetParameterAsText(1) to run from a GUI
these change every run
"""
jobName = "BestOfTheBest_Parcels138"
testFeature = ws + "\\SITES\\SurfaceParcels\\bestOfTheBest.gdb\\Best_138kVLine_analysis_combined_dissolved2"

# these stay the same every run
jobOutput = arcpy.CreateUniqueName("\\Python\\Output\\" + jobName + ".gdb")
templateGDB = "D:\\workspace\\solarSiteAnalysis\\Python\\template.gdb"
arcpy.Copy_management(templateGDB, jobOutput)
csvFile = outputTables + "\\" + jobName + ".csv"

analysis()
