# src/public_management/graph_constructor.py

import pandas as pd
import networkx as nx

def build_multigraph_from_csv(file_path: str) -> nx.MultiGraph:
    """
    Reads a CSV file containing contract data and builds a NetworkX MultiGraph.
    """
    try:
        # Define data types explicitly during CSV read to prevent errors.
        data_types = {'node_1': str, 'node_2': str, 'positive_prob': float, 'weight': float}
        df = pd.read_csv(file_path, dtype=data_types)
        
        # --- MELHORIA DE SEGURANÇA: Limpar dados reais sujos ---
        initial_len = len(df)
        df = df.dropna(subset=['node_1', 'node_2', 'positive_prob'])
        if len(df) < initial_len:
            print(f"Warning: Dropped {initial_len - len(df)} rows with missing/NaN data.")
            
        print(f"CSV file '{file_path}' loaded successfully. Found {len(df)} edges (contracts).")

        required_columns = ['node_1', 'node_2', 'positive_prob', 'weight']
        if not all(column in df.columns for column in required_columns):
            raise ValueError(f"CSV must contain the columns: {required_columns}")

        G = nx.MultiGraph()

        # Adiciona nós (garantindo que são strings sem espaços vazios extras)
        df['node_1'] = df['node_1'].astype(str).str.strip()
        df['node_2'] = df['node_2'].astype(str).str.strip()
        
        all_nodes = pd.unique(df[['node_1', 'node_2']].values.ravel('K'))
        G.add_nodes_from(all_nodes)

        # Adiciona arestas
        for index, row in df.iterrows():
            u = row['node_1']
            v = row['node_2']
            prob = float(row['positive_prob'])
            weight = float(row['weight']) if pd.notna(row['weight']) else 1.0
            
            # O parâmetro 'key' nomeia a aresta paralela, facilitando debugar depois
            G.add_edge(u, v, key=f"contract_{index}", positive_prob=prob, weight=weight)
        
        print(f"MultiGraph built successfully with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
        return G
    
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in graph_constructor: {e}")
        return None