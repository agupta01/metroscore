import logging
import os

import networkx as nx
import osmnx as ox

# Default walking speed in mph. Used to define the buffer for reachable area around nodes/edges
DEFAULT_WALK_SPEED = 3

WALK_TOLERANCE = 30
# NOTE: buffer will be built around nodes for all networks
# Will also be built around edges in road network where passenger can stop on those edges
# Working off assumption that transit vehicles only stop on nodes (note exceptions like MTA late night bus service)


def build_road_network(region: str) -> nx.MultiDiGraph:
    G = ox.graph_from_place(query=region, network_type="drive", retain_all=True)
    # TODO: clean up graph, fix speeds before returning
    return G


def build_transit_network(region: str, gtfs: os.PathLike) -> nx.MultiDiGraph:
    W = ox.graph_from_place(query=region, network_type="walk", retain_all=True)
    B = ox.graph_from_place(query=region, network_type="bike", retain_all=True)
    R = ox.graph_from_place(query=region, retain_all=True, custom_filter='["railway"~"subway"]')
    # TODO: import GTFS and filter roads to just those which have bus routes
    return W


def build_building_network(region: str) -> nx.MultiDiGraph:
    pass


def combine_graphs(a: nx.MultiDiGraph, b: nx.MultiDiGraph, buffer_size: float) -> nx.MultiDiGraph:
    """Combines two graphs, fusing them where the nodes are within a `buffer_size` distance of each other.

    Args:
        a: nx.MultiDiGraph: graph from osmnx with nodes with lat,lon coordinates
        b:
    """

    # Fuse the nodes to edges
    # if multiple transport modes, add all modes to edge like so:
    # { "mode": "walk", "speed": 3 }
    pass
