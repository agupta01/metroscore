import os
import warnings
from typing import Dict, List, Set, Tuple

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
import partridge as ptg
from partridge.gtfs import Feed
from shapely.geometry import LineString, Point
from shapely.ops import substring

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
    lines = [
        substring(ls, projections[i], projections[i + 1])
        for i in range(len(projections) - 1)
    ]
    return lines


def make_edges(df: pd.DataFrame, use_real_route_shapes: bool = True) -> pd.DataFrame:
    df = df.sort_values("stop_sequence")
    res = pd.DataFrame(
        {
            "u": df["stop_id"].values[:-1],
            "v": df["stop_id"].values[1:],
            "key": 0,
            "geometry": [
                LineString(
                    [df["stop_geometry"].values[i], df["stop_geometry"].values[i + 1]]
                )
                for i in range(len(df) - 1)
            ],
            "length": [
                df["stop_geometry"]
                .values[i]
                .distance(df["stop_geometry"].values[i + 1])
                for i in range(len(df) - 1)
            ],
            "travel_time": df["departure_time"].values[1:]
            - df["departure_time"].values[:-1],
        },
        index=None,
    )
    if use_real_route_shapes:
        # needs error handling for multiple geometries
        ls = df["trip_geometry"].values[0]
        edges = split_linestring_with_points(ls, df["stop_geometry"].tolist())
        res = res.assign(geometry=edges)
        res = res.assign(length=list(map(lambda x: x.length, edges)))
    return res


def _dedupe_per_stop_name(group, tol):
    if group.shape[0] == 1:
        group["deduped_stops"] = [set()]
        return group
    indexes_to_skip = []
    processed_indexes = []
    curr_deduped_indexes: Set[str] = set()
    deduped_stops = []

    for index, row in group.iterrows():
        geom = row["geometry"]
        curr_deduped_indexes.clear()
        if index not in indexes_to_skip:
            processed_indexes.append(index)
            indexes_to_skip.append(index)
            for other_index, other_row in group.iterrows():
                other_geom = other_row["geometry"]
                if other_index in indexes_to_skip:
                    pass
                else:
                    if geom.distance(other_geom) < tol:
                        indexes_to_skip.append(other_index)
                        curr_deduped_indexes.add(other_index)
                    else:
                        pass
        deduped_stops.append(curr_deduped_indexes.copy())
    output_gs = group.assign(deduped_stops=deduped_stops).loc[processed_indexes].copy()
    return output_gs


def deduplicate_stops(stops, tol=100):
    """
    Combine stops if they are within `tol` meters of each other and they have the same name
    If not, give them each a unique name by adding a number to the end

    Returns a DataFrame with the deduplicated stops and a dict that maps the original
    stop names to the new stop names
    """
    stops = stops.copy()
    deduplicated_stops = stops.groupby("stop_name").apply(
        _dedupe_per_stop_name,
        tol=tol,
    )
    deduplicated_stops.index = deduplicated_stops.index.get_level_values("stop_id")
    original_stop_to_deduped_stop = {
        value: key
        for key, values in zip(
            deduplicated_stops.index,
            deduplicated_stops["deduped_stops"],
        )
        for value in values
    }
    return (
        deduplicated_stops.drop(columns="deduped_stops"),
        original_stop_to_deduped_stop,
    )


def build_edge_and_node_gdf(
    feed: Feed,
) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, Dict[str | int, str | int]]:
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
                feed.stops[["stop_id", "stop_name", "geometry"]]
                .rename(columns={"geometry": "stop_geometry"})
                .dropna(subset=["stop_geometry"])
            ),
            on="stop_id",
            how="left",
        )
    )
    # confirm each trip only has one associated shape
    assert (
        combined.groupby("trip_id").apply(lambda x: x["shape_id"].nunique()).max() == 1
    )
    nodes_gdf, node_deduplication_mapping = deduplicate_stops(
        feed.stops[["stop_id", "stop_name", "geometry"]]
        .set_index("stop_id")
        .to_crs(3857),
        tol=250,
    )
    nodes_gdf = nodes_gdf.to_crs(4326)
    nodes_gdf["x"] = [p.x for p in nodes_gdf["geometry"]]
    nodes_gdf["y"] = [p.y for p in nodes_gdf["geometry"]]

    combined = combined.assign(
        stop_id=combined["stop_id"].map(lambda x: node_deduplication_mapping.get(x, x)),
    )
    edges_gdf = (
        combined.groupby("trip_id")
        .apply(make_edges, use_real_route_shapes=False)
        .set_index(["u", "v", "key"])
        .drop_duplicates()
    )

    # fiter edges to only those that have a node in nodes_gdf
    edges_gdf = edges_gdf[
        edges_gdf.index.get_level_values("u").isin(nodes_gdf.index)
        & edges_gdf.index.get_level_values("v").isin(nodes_gdf.index)
    ]

    # attach crs
    nodes_gdf = gpd.GeoDataFrame(data=nodes_gdf, geometry="geometry", crs=4326)
    edges_gdf = gpd.GeoDataFrame(data=edges_gdf, geometry="geometry", crs=4326)

    return nodes_gdf, edges_gdf, node_deduplication_mapping
