import logging
import os

import pandas as pd
from arcgis.features import Feature, FeatureSet
from arcgis.geometry import project
from arcgis.geoprocessing import LinearUnit
from arcgis.gis import GIS
from arcgis.network.analysis import generate_service_areas


def get_metro_service_areas(
    nd_path, points, cutoffs=[10, 20, 30, 40, 50, 60], time_of_day=None, verbose=0
):
    """
    Generate transit service areas for given points.

    :param nd_path: string, path to network dataset in gdb.
    :type nd_path: str
    :param points: list of (longitude, latitude) points at which to evaluate service areas.
    :type points: list[tuple[float, float]]
    :param cutoffs: list of minutes at which to generate service areas.
    Each service area will be from [0 - cutoff] for all cutoffs.
    :type cutoffs: list[int]
    :param time_of_day: datetime object to specify date and time of service area analysis.
    Default is None so analysis is time-agnostic.
    :type time_of_day: datetime.datetime
    :param verbose: turn on debug logging if set to 1. Default is 0.
    :type verbose: int
    :return: SEDF with (len(points) * len(cutoffs)) rows. Each row corresponds to one location at one cutoff time.
    :rtype: pandas.DataFrame
    """
    import arcpy
    import arcpy.nax as nax

    logger = logging.getLogger()
    if verbose == 1:
        logger.setLevel(logging.DEBUG)

    # make network dataset a layer. if it exists, use the existing one
    nd_layer_name = os.path.basename(nd_path)
    try:
        nax.MakeNetworkDatasetLayer(nd_path, nd_layer_name)
    except Exception:
        logger.debug(f"Network Dataset Layer already exists. Using {nd_layer_name}.")
    # get public transit mode
    try:
        nd_travel_modes = nax.GetTravelModes(nd_layer_name)
        transit_mode = nd_travel_modes["Public transit time"]
        logger.debug("Network Dataset Layer loaded and public transit travel mode found.")
    except KeyError:
        raise ValueError(
            f"Public Transit travel mode is not in network dataset. \
                Available transit modes include: {arcpy.nax.GetTravelModes(nd_layer_name)}"
        )

    # Instantiate a ServiceArea solver object
    service_area = nax.ServiceArea(nd_layer_name)
    # Set properties
    service_area.timeUnits = nax.TimeUnits.Minutes
    service_area.defaultImpedanceCutoffs = cutoffs
    service_area.travelMode = transit_mode
    service_area.timeOfDay = time_of_day
    service_area.geometryAtCutoff = nax.ServiceAreaPolygonCutoffGeometry.Disks
    service_area.outputType = nax.ServiceAreaOutputType.Polygons
    service_area.geometryAtOverlap = nax.ServiceAreaOverlapGeometry.Overlap
    service_area.polygonBufferDistanceUnits = nax.DistanceUnits.Meters
    service_area.polygonBufferDistance = 10.0

    logger.debug("Service Area solver created.")

    input_data = [[str(i + 1), lon, lat] for i, (lon, lat) in enumerate(points)]

    fields = ["Name", "SHAPE@"]

    # add facilities to Service Area solver object
    crs = arcpy.Describe(nd_path).spatialReference
    with service_area.insertCursor(nax.ServiceAreaInputDataType.Facilities, fields) as cur:
        for input_pt in input_data:
            pt_geom = arcpy.PointGeometry(
                arcpy.Point(input_pt[1], input_pt[2]), arcpy.SpatialReference(4326)
            ).projectAs(arcpy.SpatialReference(crs.factoryCode))
            cur.insertRow([input_pt[0], pt_geom])

    logger.debug("Facilities added.")

    # Solve the analysis
    result = service_area.solve()

    if not result.solveSucceeded:
        raise RuntimeError(
            f"Service Area solver failed with messages: {result.solverMessages(nax.MessageSeverity.All)}"
        )

    logger.debug(
        f"Service Areas solved. Computed {result.count(nax.ServiceAreaOutputDataType.Polygons)} polygons."
    )

    # export to layer
    result_path = os.path.join(os.path.dirname(nd_path), "TransitServiceAreas")
    result.export(nax.ServiceAreaOutputDataType.Polygons, result_path)
    # convert to sedf
    sedf = pd.DataFrame.spatial.from_featureclass(result_path).astype({"ToBreak": int})
    # project polygons back to 4326
    if sedf.spatial.sr["latestWkid"] != 4326:
        sedf["SHAPE"] = project(
            geometries=sedf["SHAPE"].tolist(),
            in_sr=sedf.spatial.sr,
            out_sr={"wkid": 4326, "latestWkid": 4326},
        )

    # return only the necessary columns
    return sedf[["Name", "ToBreak", "SHAPE"]]


def get_drive_time_service_areas(
    points, cutoffs=[10, 20, 30, 40, 50, 60], time_of_day=None, gis=GIS(), verbose=0
):
    """
    Generate transit service areas for given points.

    :param points: list of (longitude, latitude) points at which to evaluate service areas.
    :type points: list[tuple[float, float]]
    :param cutoffs: list of minutes at which to generate service areas.
    Each service area will be from [0 - cutoff] for all cutoffs.
    :type cutoffs: list[int]
    :param time_of_day: datetime object to specify date and time of service area analysis.
    Default is None so analysis is time-agnostic.
    :type time_of_day: datetime.datetime
    :param gis: GIS environment to use.
    :type gis: arcgis.gis.GIS
    :param verbose: turn on debug logging if set to 1. Default is 0.
    :type verbose: int
    :return: SEDF with (len(points) * len(cutoffs)) rows. Each row corresponds to one location at one cutoff time.
    :rtype: pandas.DataFrame
    """
    logger = logging.getLogger()
    if verbose == 1:
        logger.setLevel(logging.DEBUG)

    # create points Feature Set
    feat_points = [Feature(geometry={"x": p[0], "y": p[1]}) for p in points]

    fset = FeatureSet(
        feat_points,
        geometry_type="esriGeometryPoint",
        spatial_reference={"wkid": 4326, "latestWkid": 4326},
    )

    logger.debug("Created Point Feature Set.")
    # solve service area
    drive_result = generate_service_areas(
        facilities=fset,
        break_values=" ".join(map(str, cutoffs)),
        analysis_region="NorthAmerica",
        time_of_day=time_of_day,
        use_hierarchy=True,
        polygon_overlap_type="Disks",
        polygon_trim_distance=LinearUnit(10, "Meters"),
    )

    logger.debug("Solved Service Areas.")

    # create feature set of output polygons
    service_area_fset = drive_result.service_areas

    # convert to SEDF
    drive_sedf = service_area_fset.sdf
    drive_sedf["Name"] = drive_sedf["Name"].str.replace("Location ", "")

    return drive_sedf[["Name", "ToBreak", "SHAPE"]]
