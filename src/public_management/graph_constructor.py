# src/public_management/graph_constructor.py

import pandas as pd
import networkx as nx

def build_multigraph_from_csv(file_path: str) -> nx.MultiGraph:
    """
    Reads a CSV file containing contract data and builds a NetworkX MultiGraph.
    """
    try:
        # BUG FIX: Define data types explicitly during CSV read to prevent errors.
        data_types = {'node_1': str, 'node_2': str, 'positive_prob': float, 'weight': float}
        df = pd.read_csv(file_path, dtype=data_types)
        
        print(f"CSV file '{file_path}' loaded successfully. Found {len(df)} edges (contracts).")

        required_columns = ['node_1', 'node_2', 'positive_prob', 'weight']
        if not all(column in df.columns for column in required_columns):
            raise ValueError(f"CSV must contain the columns: {required_columns}")

        G = nx.MultiGraph()

        all_nodes = pd.unique(df[['node_1', 'node_2']].values.ravel('K'))
        G.add_nodes_from(all_nodes)

        for index, row in df.iterrows():
            u = row['node_1']
            v = row['node_2']
            prob = row['positive_prob']
            weight = row['weight']
            
            G.add_edge(u, v, key=f"contract_{index}", positive_prob=prob, weight=weight)
        
        print(f"MultiGraph built successfully with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
        return G
    
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in graph_constructor: {e}")
        return None