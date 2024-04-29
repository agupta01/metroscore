import warnings
from dataclasses import dataclass
from functools import cache
from typing import Any, Callable, Dict, List, Tuple
from uuid import uuid4

import osmnx as ox
from networkx import Graph
from shapely.geometry import LineString, Point

OSMEdge = Tuple[int, int, Dict]  # (u_id, v_id, data)
OSMNode = Tuple[int, Dict]  # (node_id, data)


@dataclass
class MergeMapping:
    """
    Defines mapping of nodes in graph a to nodes/edges in graph b.

    Typically, graph a is a graph with higher precedence than graph b (i.e. buses to walking).
    In this case it would make sense to merge nodes in graph a to edges in graph b but not
    vice versa.

    Attributes:
        n2n: Dict[int, OSMNode]
            Mapping of nodes ids in graph a to node ids in graph b, along with their distances.
        n2e: Dict[int, OSMEdge]
            Mapping of node ids in graph a to (node id, node id) edges in graph b,
            along with distances.
    """

    n2n: Dict[int, Tuple[int, float]]
    n2e: Dict[int, Tuple[Tuple[int, int], float]]


@dataclass
class NodeToEdgeMergeResult:
    """
    Result of merging a node to an edge.

    Attributes:
        projected_node: OSMNode
            New node projected onto edge.
        projected_edge: OSMEdge
            New edge from projected node to original node. Will have length 0.
        partitioned_edges: List[OSMEdge]
            List of edges in other graph partitioned at the projected node.
    """

    projected_node: OSMNode
    projected_edge: OSMEdge
    partitioned_edges: List[OSMEdge]


def __fill_missing_geometries(graph: Graph) -> Graph:
    """Fill missing edge geometries in graph using the geometry of the nodes."""
    n, e = ox.graph_to_gdfs(graph, nodes=True, edges=True, fill_edge_geometry=True)
    return ox.graph_from_gdfs(n, e)


def project_node_to_edge(node: OSMNode, edge: OSMEdge) -> Point:
    """
    Returns point on edge that is closest to node.

    Args:
        node: dict representing node data
        edge: tuple representing edge's data

    Returns:
        Point object representing point along edge
    """
    node_geom = Point(node[1]["x"], node[1]["y"])
    edge_geom = edge[2]["geometry"]
    interpolate_dist = edge_geom.project(node_geom)
    return edge_geom.interpolate(interpolate_dist)


def get_merge_mapping(a: Graph, b: Graph) -> MergeMapping:
    """Returns which nodes in graph b are closest to each node in graph a.
    Distances will be returned in meters.
    """
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
    nn, dists = ox.nearest_nodes(G=b, X=Xs, Y=Ys, return_dist=True)
    en, edists = ox.nearest_edges(G=b, X=Xs, Y=Ys, return_dist=True)
    en = [(u, v) for u, v, _ in en]  # remove appended '0' that's a placeholder for data
    return MergeMapping(
        n2n=dict(zip(a.nodes, zip(nn, dists))), n2e=dict(zip(a.nodes, zip(en, edists)))
    )


def merge_node_to_node(a: OSMNode, b: OSMNode) -> OSMEdge:
    """Constructs a new edge between nodes a and b. Returns tuple of new edge (with length 0)."""
    return (
        a[0],
        b[0],
        {
            "geometry": LineString([Point(a[1]["x"], a[1]["y"]), Point(b[1]["x"], b[1]["y"])]),
            "length": 0.0,
            "joined": True,
        },
    )


def merge_edge_to_node(edge: OSMEdge, node: OSMNode) -> NodeToEdgeMergeResult:
    """Constructs a new edge between edge and node. Returns new projected node along edge and edge
    from projected node to node (with length 0)."""
    projected_node_geom = project_node_to_edge(node=node, edge=edge)
    projected_node = (
        uuid4().int,
        {
            "x": projected_node_geom.x,
            "y": projected_node_geom.y,
            "lat": projected_node_geom.y,
            "lon": projected_node_geom.x,
            "geometry": projected_node_geom,
        },
    )

    u, v, data = edge
    edge_geom = data["geometry"]
    edge_length = data["length"]

    # Calculate the distance ratio of the projected point along the edge
    projected_dist = edge_geom.project(projected_node_geom)
    ratio = projected_dist / edge_length

    # Split the original edge into two new edges at the projected point
    new_edge1 = (
        u,
        projected_node[0],
        {
            "geometry": LineString([edge_geom.coords[0], projected_node_geom.coords[0]]),
            "length": edge_length * ratio,
            **{k: v for k, v in data.items() if k not in ["geometry", "length"]},
        },
    )
    new_edge2 = (
        projected_node[0],
        v,
        {
            "geometry": LineString([projected_node_geom.coords[0], edge_geom.coords[-1]]),
            "length": edge_length * (1 - ratio),
            **{k: v for k, v in data.items() if k not in ["geometry", "length"]},
        },
    )
    return NodeToEdgeMergeResult(
        projected_node=projected_node,
        projected_edge=(
            projected_node[0],
            node[0],
            {
                "geometry": LineString([projected_node_geom, Point(node[1]["x"], node[1]["y"])]),
                "length": 0.0,
                "joined": True,
            },
        ),
        partitioned_edges=[new_edge1, new_edge2],
    )


@cache
def prep_node_tuple(graph: Graph, node_id: int) -> OSMNode:
    return node_id, graph.nodes(data=True)[node_id]


def add_new_node_to_graph(graph: Graph, node: OSMNode) -> None:
    graph.add_node(node[0], **node[1])


def add_new_edge_to_graph(graph: Graph, edge: OSMEdge) -> None:
    graph.add_edge(edge[0], edge[1], **edge[2])


def merge_dicts_on_key(a: dict, b: dict, overwrite_if: Callable[[Any, Any], bool]) -> dict:
    """Merge dict `b` into dict `a`. When encountering a key that already exists in `a`,
    take the values of the conflicting key and compare them using a function `key`.
    If the output of the `key` function is True, prefer the original value from `a`.
    If the output is False, prefer the value from `b`.

    Args:
        a: dict
        b: dict
        overwrite_if: Callable[[Any, Any], bool]
            Function that takes two values and returns True if the new value is preferred,
            False otherwise.

    Returns:
        dict: Merged dictionary.
    """
    merged = a.copy()
    for k, v in b.items():
        merged[k] = v if overwrite_if(merged.get(k), v) else merged[k]
    return merged


def merge_graphs(a: Graph, other: Graph, tol: float = 100.0) -> Graph:
    """Merge `other` into `a` by connecting nodes and edges that are within
    `tol` meters of each other.

    Args:
        a: MultiDiGraph, typically the graph with higher transit precedence (i.e. rail)
        other: MultiDiGraph, typically the graph with lower transit precedence (i.e. walking)
        tol: float, default 100.0.
            Tolerance in meters for merging nodes and edges. A good heuristic is to set this
            to the number of meters an average person would be willing to walk on "non-walkable"
            surfaces (i.e. through a grassy field or parking lot).

    Returns:
        MultiDiGraph: Merged graph.
    """
    # fill missing geometries for both graphs. This implicitly deep copies the graphs as well.
    G = __fill_missing_geometries(a)
    G_O = __fill_missing_geometries(other)

    mapping = get_merge_mapping(a=G, b=G_O)
    # If a node can merge to an edge or a node, prefer the closest distance merge candidate
    # If still tied, prefer the node
    all_merges = merge_dicts_on_key(
        mapping.n2n, mapping.n2e, overwrite_if=lambda a, b: a[-1] > b[-1]
    )
    # merge nodes in O that are within tol of a
    new_nodes = []
    for n1, to_merge in all_merges.items():
        n2, dist = to_merge[0], to_merge[1]
        print(n1, n2, dist)
        if isinstance(n2, tuple) and len(n2) == 2:
            # Is edge
            if dist < tol:
                e2 = (n2[0], n2[1], G_O.get_edge_data(n2[0], n2[1])[0])
                merge_result: NodeToEdgeMergeResult = merge_edge_to_node(
                    node=prep_node_tuple(G, n1), edge=e2
                )
                # add projected edge to graph, and add new projected node to graph.
                add_new_node_to_graph(G, merge_result.projected_node)
                add_new_edge_to_graph(G, merge_result.projected_edge)
                new_nodes.append(merge_result.projected_node[0])
                # Then, add edges in O partitioned at the projected node
                # Keep original edge in O because it may be in all_merges
                add_new_edge_to_graph(G_O, merge_result.partitioned_edges[0])
                add_new_edge_to_graph(G_O, merge_result.partitioned_edges[1])

        elif isinstance(n2, int):
            # Is node
            if dist < tol:
                new_edge: OSMEdge = merge_node_to_node(
                    a=prep_node_tuple(G, n1), b=prep_node_tuple(G_O, n2)
                )
                add_new_edge_to_graph(G, new_edge)
                new_nodes.append(new_edge[1])
        else:
            raise ValueError(f"Invalid merge mapping from {n1} to {to_merge}")
    print(len(new_nodes))
    G.add_nodes_from(G_O.nodes(data=True))
    G.add_edges_from(G_O.edges(data=True))
    return G
