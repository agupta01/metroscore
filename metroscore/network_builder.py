import os
import warnings
from functools import partial
from typing import List, Tuple

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
import partridge as ptg
from partridge.gtfs import Feed
from pyproj import CRS
from shapely.geometry import LineString, Point
from shapely.ops import substring

# Default walking speed in mph. Used to define the buffer for reachable area around nodes/edges
DEFAULT_WALK_SPEED = 3

WALK_TOLERANCE = 30
# NOTE: buffer will be built around nodes for all networks
# Will also be built around edges in road network where passenger can stop on those edges
# Working off assumption that transit vehicles only stop on nodes (note exceptions like MTA late night bus service)


def build_road_network(region: str) -> nx.MultiDiGraph:
    G = ox.graph_from_place(query=region, network_type="drive", retain_all=True)
    G = ox.project_graph(G)
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    return G


def build_transit_network(region: str, gtfs: os.PathLike) -> nx.MultiDiGraph:
    W = ox.graph_from_place(query=region, network_type="walk", retain_all=True)
    # B = ox.graph_from_place(query=region, network_type="bike", retain_all=True)
    # R = ox.graph_from_place(query=region, retain_all=True, custom_filter='["railway"~"subway"]')
    # TODO: import GTFS and filter roads to just those which have bus routes
    return W


def build_building_network(region: str) -> nx.MultiDiGraph:
    # TODO: implement
    return nx.MultiDiGraph()


def load_gtfs_feed(gtfs: str) -> Feed:
    service_ids = ptg.read_busiest_date(gtfs)[1]
    view = {"trips.txt": {"service_id": service_ids}}

    return ptg.load_geo_feed(gtfs, view)


def split_linestring_with_points(ls: LineString, p: List[Point]) -> List[LineString]:
    # get distance projections of points to linestring
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        projections = [ls.project(p) for p in p]
    # sort projections
    projections.sort()
    # split lineßstring
    lines = [substring(ls, projections[i], projections[i + 1]) for i in range(len(projections) - 1)]
    return lines


def make_edges(df: pd.DataFrame, use_real_route_shapes: bool = True) -> pd.DataFrame:
    df = df.sort_values("stop_sequence")
    res = pd.DataFrame(
        {
            "u": df["stop_id"].values[:-1],
            "v": df["stop_id"].values[1:],
            "key": 0,
            "geometry": [
                LineString([df["stop_geometry"].values[i], df["stop_geometry"].values[i + 1]])
                for i in range(len(df) - 1)
            ],
            "length": [
                df["stop_geometry"].values[i].distance(df["stop_geometry"].values[i + 1])
                for i in range(len(df) - 1)
            ],
            "travel_time": df["departure_time"].values[1:] - df["departure_time"].values[:-1],
        },
        index=None,
    )
    if use_real_route_shapes:
        ls = df["trip_geometry"].values[0]  # needs error handling for multiple geometries
        edges = split_linestring_with_points(ls, df["stop_geometry"].tolist())
        res = res.assign(geometry=edges)
        res = res.assign(length=list(map(lambda x: x.length, edges)))
    return res


fast_make_edges = partial(make_edges, use_real_route_shapes=False)


def build_edge_and_node_gdf(feed: Feed) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    combined = (
        feed.stop_times[["trip_id", "stop_id", "departure_time", "stop_sequence"]]
        .merge(feed.trips[["trip_id", "shape_id"]], on="trip_id", how="left")
        .merge(
            (
                feed.shapes.rename(columns={"geometry": "trip_geometry"}).dropna(
                    subset=["trip_geometry"]
                )
            ),
            on="shape_id",
            how="left",
        )
        .merge(
            (
                feed.stops[["stop_id", "geometry"]]
                .rename(columns={"geometry": "stop_geometry"})
                .dropna(subset=["stop_geometry"])
            ),
            on="stop_id",
            how="left",
        )
    )
    # confirm each trip only has one associated shape
    print(combined.groupby("trip_id").apply(lambda x: x["shape_id"].nunique()).max() == 1)
    edges_gdf = (
        combined.groupby("trip_id")
        .apply(fast_make_edges)
        .set_index(["u", "v", "key"])
        .drop_duplicates()
    )
    nodes_gdf = feed.stops[["stop_id", "geometry"]].set_index("stop_id")
    nodes_gdf["x"] = nodes_gdf["geometry"].x
    nodes_gdf["y"] = nodes_gdf["geometry"].y

    # attach crs
    crs = CRS.from_user_input(4326)
    nodes_gdf.crs = crs
    edges_gdf.crs = crs

    return nodes_gdf, edges_gdf
