import os
import logging
import numpy as np
import pandas as pd
from arcgis.gis import GIS
import arcpy

def make_random_points(polygon, N=10):
    """
    Creates `N` random points within the polygon `polygon`.
    """
    points = []
    minx, miny, maxx, maxy = polygon.extent
    while len(points) < N:
        pnt = Point({"x":np.random.uniform(minx, maxx), "y":np.random.uniform(miny, maxy)})
        if polygon.contains(pnt):
            points.append(tuple(pnt.coordinates()))
    return points

def get_metro_service_areas(nd_path, points, cutoffs=[10,20,30,40,50,60], time_of_day=None, verbose=0):
    """
    Generate transit service areas for given points.
    
    Parameters
    ----------
    nd_path: string, path to network dataset in gdb.
    points: list of (longitude, latitude) points at which to evaluate service areas.
    cutoffs: list of minutes at which to generate service areas. Each service area will be from [0 - cutoff] for all cutoffs.
    time_of_day: datetime object to specify date and time of service area analysis. Default is None so analysis is time-agnostic.
    verbose: turn on debug logging if set to 1. Default is 0.
    
    Returns
    -------
    SEDF with (len(points) * len(cutoffs)) rows.
    Each row corresponds to one location at one cutoff time.
    """
    logger = logging.getLogger()
    if verbose == 1:
        logger.setLevel(logging.DEBUG)
    
    # make network dataset a layer. if it exists, use the existing one
    nd_layer_name = os.path.basename(nd_path)
    try:
        arcpy.nax.MakeNetworkDatasetLayer(nd_path, nd_layer_name)
    except:
        logger.debug(f"Network Dataset Layer already exists. Using {nd_layer_name}.")
    # get public transit mode
    try:
        nd_travel_modes = arcpy.nax.GetTravelModes(nd_layer_name)
        transit_mode = nd_travel_modes["Public transit time"]
        logger.debug("Network Dataset Layer loaded and public transit travel mode found.")
    except KeyError:
        raise ValueError(f"Public Transit travel mode is not in network dataset. Available transit modes include: {arcpy.nax.GetTravelModes(nd_layer_name)}")
    
    
    # Instantiate a ServiceArea solver object
    service_area = arcpy.nax.ServiceArea(nd_layer_name)
    # Set properties
    service_area.timeUnits = arcpy.nax.TimeUnits.Minutes
    service_area.defaultImpedanceCutoffs = cutoffs
    service_area.travelMode = transit_mode
    service_area.geometryAtCutoff = arcpy.nax.ServiceAreaPolygonCutoffGeometry.Disks
    service_area.outputType = arcpy.nax.ServiceAreaOutputType.Polygons
    service_area.geometryAtOverlap = arcpy.nax.ServiceAreaOverlapGeometry.Overlap
    service_area.polygonBufferDistanceUnits = arcpy.nax.DistanceUnits.Meters
    service_area.polygonBufferDistance = 10.0
    
    logger.debug("Service Area solver created.")
    
    # instantiate facilities
    input_data = [[str(i+1), lon, lat] for i, (lon, lat) in enumerate(points)]

    fields = ["Name", "SHAPE@"]

    # add facilities to Service Area solver object
    crs = arcpy.Describe(nd_path).spatialReference
    with service_area.insertCursor(arcpy.nax.ServiceAreaInputDataType.Facilities, fields) as cur:
        for input_pt in input_data:
            pt_geom = arcpy.PointGeometry(arcpy.Point(input_pt[1], input_pt[2]), crs)
            cur.insertRow([input_pt[0], pt_geom])
        
    logger.debug("Facilities added.")
    
    # Solve the analysis
    result = service_area.solve()
    
    if not result.solveSucceeded:
        raise RuntimeError(f"Service Area solver failed with messages: {result.solverMessages(arcpy.nax.MessageSeverity.All)}")
    
    logger.debug(f"Service Areas solved. Computed {result.count(arcpy.nax.ServiceAreaOutputDataType.Polygons)} polygons.")
    
    # export to layer
    result_path = os.path.join(os.path.dirname(nd_path), "TransitServiceAreas")
    result.export(arcpy.nax.ServiceAreaOutputDataType.Polygons, result_path)
    # convert to sedf
    sedf = pd.DataFrame.spatial.from_featureclass(result_path).astype({'ToBreak': int})
    
    # return only the necessary columns
    return sedf[["Name", "ToBreak", "SHAPE"]]


def get_drive_time_service_areas(points, cutoffs=[10,20,30,40,50,60], time_of_day=None, gis=gis, verbose=0):
    """
    Generate transit service areas for given points.
    
    Parameters
    ----------
    points: list of (longitude, latitude) points at which to evaluate service areas.
    cutoffs: list of minutes at which to generate service areas. Each service area will be from [0 - cutoff] for all cutoffs.
    time_of_day: datetime object to specify date and time of service area analysis. Default is None so analysis is time-agnostic.
    gis: GIS environment to use.
    verbose: turn on debug logging if set to 1. Default is 0.
    
    Returns
    -------
    SEDF with (len(points) * len(cutoffs)) rows.
    Each row corresponds to one location at one cutoff time.
    """
    logger = logging.getLogger()
    if verbose == 1:
        logger.setLevel(logging.DEBUG)
    
    # create service area
    service_area_url = gis.properties.helperServices.serviceArea.url
    sa_layer = network.ServiceAreaLayer(service_area_url, gis=gis)
    
    # create points Feature Set
    feat_points = [Feature(geometry={"x":p[0], "y":p[1]}) for p in points]

    fset = FeatureSet(feat_points, geometry_type='esriGeometryPoint', 
                                spatial_reference={'wkid': 4326, 'latestWkid': 4326})
    logger.debug("Created Point Feature Set.")
    # solve service area
    drive_result = sa_layer.solve_service_area(
        fset, 
        default_breaks=cutoffs, 
        travel_direction='esriNATravelDirectionFromFacility', 
        split_polygons_at_breaks=False,
        trim_polygon_distance=10.0,
    )
    
    logger.debug("Solved Service Areas.")
    
    # create feature set of output polygons
    poly_feat_list = []
    for polygon_dict in drive_result['saPolygons']['features']:
        f1 = Feature(polygon_dict['geometry'], polygon_dict['attributes'])
        poly_feat_list.append(f1)
    
    service_area_fset = FeatureSet(
        poly_feat_list, 
        geometry_type=drive_result['saPolygons']['geometryType'],
        spatial_reference= drive_result['saPolygons']['spatialReference']
    )
    
    # convert to SEDF
    drive_sedf = service_area_fset.sdf
    drive_sedf["Name"] = drive_sedf['Name'].str.replace('Location ', "")
    
    return drive_sedf[["Name", "ToBreak", "SHAPE"]]
    

def compute_metroscore(transit_sedf, drive_sedf, bonus_weight=2.0, return_all=False):
    """
    Computes the row-wise metroscore for each computed service area.
    
    Parameters
    ----------
    transit_sedf: SEDF with shapes of transit service areas and unique names of format "<Facility ID> : <FromBreak> - <ToBreak>".
    drive_sedf: SEDF with shapes of drive-time service areas and unique names matching those in `transit_sedf`.
    bonus_weight: float (Default 2.0) of weightage to give to transit bonus.
    return_all: bool (Default False) whether to return all columns (including intermediate steps) or just the final metroscore.
    
    Returns
    -------
    Pandas DataFrame with schema:
    {
        "Name": (str) unique service area names of format "<Facility ID> : <FromBreak> - <ToBreak>",
        "Metroscore": (float) metroscore of service area 
    }
    """
    # merge transit and drive sedfs
    joined_sa = pd.merge(
        left=sedf[['Name', 'SHAPE']], 
        right=drive_sedf[['Name', 'SHAPE']], 
        on='Name', how='inner', 
        suffixes=('_transit', '_drive')
    ).astype({"SHAPE_transit": "geometry", "SHAPE_drive": "geometry"})
    
    # compute preliminaries
    joined_sa["area(D)"] = joined_sa.SHAPE_drive.geom.area
    joined_sa["area(D - T)"] = joined_sa.SHAPE_drive.geom.difference(joined_sa.SHAPE_transit).geom.area
    joined_sa["area(T - D)"] = joined_sa.SHAPE_transit.geom.difference(joined_sa.SHAPE_drive).geom.area.fillna(0.0) # when the difference is a null set arcgis returns NaN
    
    # compute TDTC and TB
    joined_sa["TDTC"] = (joined_sa["area(D)"] - joined_sa["area(D - T)"]) / joined_sa["area(D)"]
    joined_sa["TB"] = joined_sa["area(T - D)"] / joined_sa["area(D)"]
    
    # compute final metroscore
    joined_sa["Metroscore"] = joined_sa["TDTC"] + (bonus_weight * joined_sa["TB"])
    
    if return_all:
        return joined_sa
    else:
        return joined_sa[['Name', 'Metroscore']]
