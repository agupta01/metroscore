import networkx as nx
import numpy as np
import pandas as pd

from metroscore.service_areas import (
    floyd_warshall_fast,
    floyd_warshall_slow,
    time_dependent_a_star,
    time_dependent_dijkstra,
)


def test_floyd_warshall_small_matrix():
    INPUT = np.array(
        [
            [0.0, np.inf, -2.0, np.inf],
            [4.0, 0.0, 3.0, np.inf],
            [np.inf, np.inf, 0.0, 2.0],
            [np.inf, -1.0, np.inf, 0.0],
        ]
    )

    OUTPUT = np.array(
        [
            [0.0, -1.0, -2.0, 0.0],
            [4.0, 0.0, 2.0, 4.0],
            [5.0, 1.0, 0.0, 2.0],
            [3.0, -1.0, 1.0, 0.0],
        ]
    )

    assert np.allclose(floyd_warshall_fast(INPUT), OUTPUT)
    assert np.allclose(floyd_warshall_slow(INPUT), OUTPUT)


def test_tdsp_djikstra():
    G = nx.DiGraph()
    G.add_edges_from(
        [
            (1, 2, {"travel_time": 6}),
            (1, 3, {"travel_time": 10}),
            (2, 3, {"travel_time": 3}),
            (3, 4, {"travel_time": 5}),
            (2, 4, {"travel_time": 12}),
        ]
    )
    every_second = list(range(86400))
    timetable = pd.Series(
        data=[every_second] * 5,
        index=pd.MultiIndex.from_tuples([(1, 2), (1, 3), (2, 3), (3, 4), (2, 4)]),
    )
    start_time = 4
    origin_id = 1
    result = time_dependent_dijkstra(G, timetable, start_time, origin_id)

    assert result[1] == 4
    assert result[2] == 10
    assert result[3] == 13
    assert result[4] == 18


def test_tdsp_a_star():
    G = nx.DiGraph()
    G.add_edges_from(
        [
            (1, 2, {"travel_time": 6}),
            (1, 3, {"travel_time": 10}),
            (2, 3, {"travel_time": 3}),
            (3, 4, {"travel_time": 5}),
            (2, 4, {"travel_time": 12}),
        ]
    )
    every_second = list(range(86400))
    timetable = pd.Series(
        data=[every_second] * 5,
        index=pd.MultiIndex.from_tuples([(1, 2), (1, 3), (2, 3), (3, 4), (2, 4)]),
    )
    start_time = 4
    origin_id = 1
    result = time_dependent_a_star(G, timetable, start_time, origin_id)

    assert result[1] == 4
    assert result[2] == 10
    assert result[3] == 13
    assert result[4] == 18


def test_tdsp_djikstra_every_other_second():
    """Departure times at all nodes are every other second."""
    G = nx.DiGraph()
    G.add_edges_from(
        [
            (1, 2, {"travel_time": 6}),
            (1, 3, {"travel_time": 10}),
            (2, 3, {"travel_time": 3}),
            (3, 4, {"travel_time": 5}),
            (2, 4, {"travel_time": 12}),
        ]
    )
    every_other_second = list(range(0, 86400, 2))
    timetable = pd.Series(
        data=[every_other_second] * 5,
        index=pd.MultiIndex.from_tuples([(1, 2), (1, 3), (2, 3), (3, 4), (2, 4)]),
    )
    start_time = 4
    origin_id = 1
    result = time_dependent_dijkstra(G, timetable, start_time, origin_id)

    assert result[1] == 4
    assert result[2] == 10
    assert result[3] == 13
    assert result[4] == 19
