import warnings
from functools import cache
from typing import Dict, Tuple

import networkx as nx
import osmnx as ox
from geopy.distance import distance, lonlat
from networkx import Graph, MultiDiGraph
from shapely.geometry import Point


def __fill_missing_geometries(graph: Graph) -> Graph:
    """Fill missing edge geometries in graph using the geometry of the nodes."""
    n, e = ox.graph_to_gdfs(graph, nodes=True, edges=True, fill_edge_geometry=True)
    return ox.graph_from_gdfs(n, e)


def project_node_to_edge(node: Dict, edge: Tuple) -> Point:
    """
    Returns point on edge that is closest to node.

    Args:
        node: dict representing node data
        edge: tuple representing edge's data

    Returns:
        Point object representing point along edge
    """
    node_geom = Point(node["x"], node["y"])
    edge_geom = edge[2]["geometry"]
    interpolate_dist = edge_geom.project(node_geom)
    return edge_geom.interpolate(interpolate_dist)


def get_node_to_node_mapping(a: Graph, b: Graph) -> Dict[int, int]:
    """Returns which nodes in graph b are closest to each node in graph a."""
    # project graph if not done so
    a = ox.project_graph(a, to_latlong=True)
    b = ox.project_graph(b, to_latlong=True)
    Xs = []
    Ys = []
    for _id, node in a.nodes(data=True):
        if (node["x"] != node["lon"]) or (node["y"] != node["lat"]):
            warnings.warn(
                "Mismatched coordinates found. "
                + "Lon/lat do not match x/y coordinates. "
                + "When this happens, metroscore will use the x/y coordinates.\n"
                + f"Offending node: {_id}"
            )
        Xs.append(node["x"])
        Ys.append(node["y"])
    nn = ox.nearest_nodes(G=b, X=Xs, Y=Ys)
    return dict(zip(a.nodes, nn))


def merge_node_to_node(a: Tuple[int, Dict], b: Tuple[int, Dict]) -> Tuple[int, Dict]:
    """Constructs a new node at the centroid of nodes a and b. Returns tuple of node id and data."""
    new_x = (a[1]["x"] + b[1]["x"]) / 2
    new_y = (a[1]["y"] + b[1]["y"]) / 2
    # keep a's node id
    return a[0], {"x": new_x, "y": new_y, "lon": new_x, "lat": new_y, "merge_provenance": b[0]}


@cache
def __prep_node_tuple(graph: Graph, node_id: int) -> Tuple[int, Dict]:
    return node_id, graph.nodes(data=True)[node_id]


def merge_graphs(a: MultiDiGraph, other: MultiDiGraph, tol: float = 20.0) -> Graph:
    """Merge `other` into `a` by connecting nodes that are within `tol` meters of each other.
    Also merge the edges.

    Args:
        a: MultiDiGraph
        other: MultiDiGraph
        tol: float, default 20.
            Tolerance in meters for merging nodes.

    Returns:
        MultiDiGraph: Merged graph.
    """
    # make a copy of a
    G = a.copy()
    G_x = nx.get_node_attributes(G, "x")
    G_y = nx.get_node_attributes(G, "y")
    O_x = nx.get_node_attributes(other, "x")
    O_y = nx.get_node_attributes(other, "y")
    # get node to node mapping for other
    mapping = get_node_to_node_mapping(a=G, b=other)
    # merge nodes in other that are within tol of a
    new_node_attributes = {}
    for n1, n2 in mapping.items():
        dist = distance(lonlat(G_x[n1], G_y[n1]), lonlat(O_x[n2], O_y[n2])).m
        if dist < tol:
            # print(f"Merging nodes {n1} and {n2} at distance {dist:.2f}m")
            node_id, node_attributes = merge_node_to_node(
                a=__prep_node_tuple(G, n1), b=__prep_node_tuple(other, n2)
            )
            new_node_attributes[node_id] = node_attributes
        else:
            # print(f"Nodes {n1} and {n2} are too far apart at distance {dist:.2f}m")
            pass
    nx.set_node_attributes(G, new_node_attributes)
    return G
