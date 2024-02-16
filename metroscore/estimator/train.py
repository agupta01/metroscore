import torch
import networkx as nx
import osmnx as ox

def load_road_data(origin: str) -> nx.Graph:
	G = ox.graph_from_place(origin, network_type="drive")
	return G

