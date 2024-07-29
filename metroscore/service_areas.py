import heapq
from typing import Any, Dict, List, Optional, Set

import geopandas as gpd
import numpy as np
import pandas as pd
from geopandas import GeoDataFrame
from networkx import MultiGraph
from shapely import unary_union
from shapely.geometry import MultiPolygon, Polygon

# Default walking speed in m/s. Used to define the buffer for reachable area around nodes/edges
DEFAULT_WALK_SPEED = 1.42


def validate_adjacency_matrix(adj: np.ndarray):
    """
    Validate the adjacency matrix for Modified Floyd-Warshall algorithm.
    """
    n, k = adj.shape
    if n != k:
        raise ValueError("Adjacency matrix must be square.")
    if not np.allclose(np.diagonal(adj), 0):
        raise ValueError("Diagonal elements of adjacency matrix must be zero.")


def floyd_warshall_fast(adj: np.ndarray) -> np.ndarray:
    validate_adjacency_matrix(adj)

    for k in range(adj.shape[0]):
        adj = np.minimum(adj, adj[np.newaxis, k, :] + adj[:, k, np.newaxis])

    return adj


def floyd_warshall_slow(adj: np.ndarray) -> np.ndarray:
    # validate_adjacency_matrix(adj)

    n = adj.shape[0]
    for k in range(n):
        for i in range(n):
            for j in range(n):
                adj[i, j] = min(adj[i, j], adj[i, k] + adj[k, j])

    return adj


def time_dependent_dijkstra(
    G: MultiGraph,
    timetable: pd.Series,
    start_time: float,
    origin_id: Any,
) -> Dict[int, float]:
    """
    Implements a modified Djikstra algorithm that finds the time-dependent shortest path from
    origin node to all other nodes in the graph.

    Args:
        G (Graph): NetworkX Graph object.
        stop_times (pd.Series): Departure times. Index is a tuple of (from, to)
            node IDs. Values are in seconds (since midnight.)
        start_time (float): Current time.
        origin_id (Any): Origin node ID.

    Returns:
        Dict[int, float]: Dictionary of node IDs and arrival times, in seconds.

    Based on algorithm outlined in Stephen Boyles' lecture:
    https://sboyles.github.io/teaching/ce392d/8-tdsp.pdf
    """
    # Initialization step
    N = len(G.nodes)
    L = {_id: np.inf for _id in G.nodes}  # travel time from origin to node
    q = {_id: -1 for _id in G.nodes}  # q is the predecessor node
    F: Set[int] = set()  # set of settled nodes

    L[origin_id] = start_time

    while len(F) < N:
        curr_id = min(((x, y) for x, y in L.items() if x not in F), key=lambda x: x[1])[
            0
        ]
        curr_time = L[curr_id]
        F.add(curr_id)
        for candidate_id in G.neighbors(curr_id):
            if candidate_id in F:
                continue
            # wait time is next departure time - current time in day
            wait_time = get_next_departure_time(
                curr_time,
                curr_id,
                candidate_id,
                timetable,
            ) - (curr_time % 86400)
            try:
                travel_time = G.get_edge_data(curr_id, candidate_id)["travel_time"]
            except KeyError:
                travel_time = G.get_edge_data(curr_id, candidate_id, key=0)[
                    "travel_time"
                ]
            if L[candidate_id] > curr_time + travel_time + wait_time:
                L[candidate_id] = curr_time + travel_time + wait_time
                q[candidate_id] = curr_id

    return L


def time_dependent_a_star(
    G: MultiGraph, timetable: pd.Series, start_time: float, origin_id: Any
) -> Dict[int, float]:
    """
    Implements a modified A* algorithm that finds the time-dependent shortest path from
    origin node to all other nodes in the graph.

    Args:
        G (Graph): NetworkX Graph object.
        timetable (pd.Series): Departure times. Index is a tuple of (from, to)
            node IDs. Values are in seconds (since midnight).
        start_time (float): Current time.
        origin_id (Any): Origin node ID.

    Returns:
        Dict[int, float]: Dictionary of node IDs and arrival times, in seconds.
    """

    def _zero_heuristic(G: MultiGraph, target_id: Any) -> Dict[Any, float]:
        heuristic = {}
        for node in G.nodes:
            heuristic[node] = 0.0
        return heuristic

    L = {_id: np.inf for _id in G.nodes}  # travel time from origin to node
    q = {_id: -1 for _id in G.nodes}  # q is the predecessor node
    F: Set[int] = set()  # set of settled nodes

    heuristic = _zero_heuristic(G, origin_id)
    L[origin_id] = start_time
    counter = 0  # Use a counter to ensure unique and consistent ordering in the priority queue
    priority_queue = [
        (start_time + heuristic[origin_id], start_time, counter, origin_id)
    ]  # (f_score, g_score, counter, node)
    counter += 1

    while priority_queue:
        _, curr_time, _, curr_id = heapq.heappop(priority_queue)
        if curr_id in F:
            continue
        F.add(curr_id)

        for candidate_id in G.neighbors(curr_id):
            if candidate_id in F:
                continue
            wait_time = get_next_departure_time(
                curr_time,
                curr_id,
                candidate_id,
                timetable,
            ) - (curr_time % 86400)
            try:
                travel_time = G.get_edge_data(curr_id, candidate_id)["travel_time"]
            except KeyError:
                travel_time = G.get_edge_data(curr_id, candidate_id, key=0)[
                    "travel_time"
                ]
            tentative_g_score = curr_time + travel_time + wait_time
            if L[candidate_id] > tentative_g_score:
                L[candidate_id] = tentative_g_score
                f_score = tentative_g_score + heuristic[candidate_id]
                heapq.heappush(
                    priority_queue, (f_score, tentative_g_score, counter, candidate_id)
                )  # Add counter for tie-breaking
                counter += 1
                q[candidate_id] = curr_id

    return L


def get_next_departure_time(
    curr_time: float,
    origin_id: int,
    dest_id: int,
    timetable: pd.Series,
):
    """
    Get the departure time from origin node to destination node.
    """
    daily_curr_time = curr_time % 86000
    # binary insert the current time into the timetable for origin to destination
    if (origin_id, dest_id) not in timetable.index:
        return curr_time  # no timetable for this route, assume no wait time
    timetable_for_route = timetable.loc[(origin_id, dest_id)]
    next_departure_time_idx = np.searchsorted(
        timetable_for_route,
        daily_curr_time,
        side="left",
    )
    if next_departure_time_idx == len(timetable_for_route):
        return timetable_for_route[0]  # wrap around if we miss last transit of day
    return timetable_for_route[next_departure_time_idx]


def get_transit_areas(
    travel_times: Dict[int, float],
    cutoffs: List[float],
    node_gdf: gpd.GeoDataFrame,
    use_walking_buffer: bool = False,
) -> gpd.GeoSeries:
    """
    Get the polygons of reachable areas from a given origin.

    Args:
        travel_times (Dict[int, float]): Dictionary of node IDs and travel times.
        cutoffs (List[float]): List of travel time cutoffs.
        node_gdf (gpd.GeoDataFrame): GeoDataFrame of nodes and their locations (Points).
            Should be indexed by stop_id.
        use_walking_buffer (bool, optional): Whether to use a walking buffer around nodes.
            Defaults to False. If true, buffers are computed around all reachable nodes
            using the remaining time until the cutoff is reached. This can result in
            overly "spherical" transit areas that ignore geographical features
            like bodies of water. If false, the buffer around each reachable node
            is constant and small. When used with a properly configured graph that
            contains walking nodes, this can result in more realistic transit areas.


    Note that it is assumed that the travel times in `travel_times` and `cutoffs`
    are in the same units.

    Returns:
        GeoSeries of travel time cutoffs and reachable areas.
    """

    # TODO: this can be optimized by appending to exisiting unary union for each new
    # cutoff value
    def _get_reachable_polygon_for_cutoff(
        cutoff: float,
    ) -> Optional[Polygon | MultiPolygon]:
        reachable = list(filter(lambda x: x[1] < cutoff, travel_times.items()))
        if not reachable:
            return None
        if use_walking_buffer:
            reachable_with_buffers = list(
                map(
                    lambda x: (x[0], x[1], DEFAULT_WALK_SPEED * (cutoff - x[1])),
                    reachable,
                )
            )
        else:  # use constant buffer
            reachable_with_buffers = list(
                map(lambda x: (x[0], x[1], DEFAULT_WALK_SPEED * 60), reachable)
            )
        reachable_with_buffers = pd.DataFrame(
            reachable_with_buffers,
            columns=["stop_id", "time_to_node", "buffer_at_node"],
        ).set_index("stop_id")
        reachable_with_buffers_gpd: GeoDataFrame = GeoDataFrame(
            reachable_with_buffers.merge(  # type: ignore
                node_gdf[["geometry"]],
                left_index=True,
                right_index=True,
                how="left",
            ),
            geometry="geometry",
            crs=node_gdf.crs,
        ).to_crs(3857)
        buffered_col = reachable_with_buffers_gpd["geometry"].buffer(  # type: ignore
            reachable_with_buffers["buffer_at_node"]  # type: ignore
        )
        return unary_union(buffered_col)  # type: ignore

    reachable_areas = {
        cutoff: _get_reachable_polygon_for_cutoff(cutoff) for cutoff in cutoffs
    }
    # return reachable_areas

    return gpd.GeoSeries(
        data=reachable_areas,
        crs=node_gdf.crs,
    )
