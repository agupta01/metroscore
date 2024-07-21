import networkx as nx
from pyproj import CRS

import metroscore.utils as mu


def test_add_new_edge_to_graph():
    G = nx.MultiGraph()
    G.add_node(1)
    G.add_node(2)
    mu.add_new_edge_to_graph(G, (1, 2, {"travel_time": 3}))
    assert G.get_edge_data(1, 2)[0]["travel_time"] == 3


def test_add_new_node_to_graph():
    G = nx.Graph()
    mu.add_new_node_to_graph(G, (1, {}))
    assert 1 in G.nodes


def test_graph_merge_node_to_node():
    A = nx.MultiDiGraph(crs=CRS.from_epsg(4326))
    B = nx.MultiDiGraph(crs=CRS.from_epsg(4326))

    A.add_node(1, x=-73.9612924, y=40.818477200000004)
    A.add_node(2, x=0.0, y=0.0)
    A.add_edge(1, 2, length=1000.0)
    B.add_node(3, x=-73.9618103, y=40.8180007)
    B.add_node(4, x=0.0, y=90.0)
    B.add_edge(3, 4, length=1000.0)

    merged = mu.merge_graphs(a=A, other=B, tol=100)

    assert 1 in merged.nodes
    assert 2 in merged.nodes
    assert 3 in merged.nodes
    assert 4 in merged.nodes
    assert merged.get_edge_data(1, 3, key=0)["length"] == 0.0
    assert merged.get_edge_data(3, 4, key=0)["length"] == 1000.0
