from shapely.geometry import Point, LineString
from typing import Tuple, Dict
from networkx import MultiDiGraph
import osmnx as ox
import warnings


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
    interpolate_dist = edge_geom.project(node)
    return edge_geom.interpolate(interpolate_dist)


def get_node_to_node_mapping(a: MultiDiGraph, b: MultiDiGraph) -> Dict[int, Tuple[int, int]]:
    """Returns which nodes in graph b are closest to each node in graph a, along with their distances."""
    # project graph if not done so
    a = ox.projection.project_graph(a, to_latlong=True)
    b = ox.projection.project_graph(b, to_latlong=True)
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
    nn, dist = ox.distance.nearest_nodes(G=b, X=Xs, Y=Ys, return_dist=True)
    return dict(zip(a.nodes, zip(nn, dist)))


def merge_node_to_node(a: Tuple[int, Dict], b: Tuple[int, Dict]) -> Tuple[int, Dict]:
    """Constructs a new node at the centroid of nodes a and b. Returns tuple of node id and data."""
    new_x = (a[1]["x"] + b[1]["x"]) / 2
    new_y = (a[1]["y"] + b[1]["y"]) / 2
    # keep a's node id
    return a[0], {"x": new_x, "y": new_y, "lon": new_x, "lat": new_y}
