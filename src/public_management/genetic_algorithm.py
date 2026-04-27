# src/public_management/genetic_algorithm.py

# --- Imports ---
import networkx as nx
from typing import List, Dict, Tuple
from deap import base, creator, tools, algorithms
import random

def evaluate_fitness(
    chromosome: List[int], 
    nodes_map: Dict[int, str], 
    G: nx.MultiGraph,
    aggregated_edges: Dict[tuple, Dict[str, float]] = None
) -> Tuple[float, int]:
    """
    [English]
    Calculates the fitness of a given chromosome based on two objectives:
    1. Expected disagreement (to be minimized).
    2. Number of clusters (to be minimized).
    
    Optimized for MultiGraphs by using pre-aggregated edge penalties.
    """
    # --- Step 1: Translate chromosome into a more usable partition map ---
    # Convert chromosome indices to actual node names representing their cluster center
    partition = {nodes_map[i]: nodes_map[chromosome[i]] for i in range(len(chromosome))}

    # --- Step 2: Calculate f1 (Expected Disagreement) ---
    disagreement = 0.0
    
    # OTIMIZAÇÃO: Usa arestas pré-agregadas se disponíveis (muito mais rápido para o AG)
    if aggregated_edges is not None:
        for (u, v), penalties in aggregated_edges.items():
            if partition[u] == partition[v]:
                # Estão no mesmo cluster: pagam o custo das arestas que deveriam ser negativas
                disagreement += penalties['neg']
            else:
                # Estão em clusters diferentes: pagam o custo das arestas que deveriam ser positivas
                disagreement += penalties['pos']
    else:
        # Fallback seguro caso o grafo não tenha sido pré-agregado (ex: testes simples)
        # Atenção: num MultiGraph, edges(keys=True) retorna (u, v, k, data)
        edges_iter = G.edges(keys=True, data=True) if isinstance(G, nx.MultiGraph) else G.edges(data=True)
        
        for edge_info in edges_iter:
            if len(edge_info) == 4:
                u, v, k, data = edge_info
            else:
                u, v, data = edge_info
                
            p_e = data.get('positive_prob', 0.5)
            w_e = data.get('weight', 1.0)
            
            if partition[u] == partition[v]:
                disagreement += w_e * (1 - p_e)
            else:
                disagreement += w_e * p_e

    # --- Step 3: Calculate f2 (Number of Clusters) ---
    # The number of unique representatives in the chromosome
    num_clusters = len(set(chromosome))

    return disagreement, num_clusters


def setup_genetic_algorithm(nodes: List[str], G: nx.MultiGraph):
    """
    [English]
    Configures the DEAP toolbox for the Multi-Objective Genetic Algorithm (NSGA-II).
    Pre-aggregates MultiGraph edges to speed up the fitness evaluation.
    """
    # --- 0. Pre-aggregate MultiGraph edges for immense speedup ---
    aggregated_edges = {}
    
    edges_iter = G.edges(keys=True, data=True) if isinstance(G, nx.MultiGraph) else G.edges(data=True)
    
    for edge_info in edges_iter:
        if len(edge_info) == 4:
            u, v, k, data = edge_info
        else:
            u, v, data = edge_info
            
        u_str, v_str = str(u), str(v)
        if u_str == v_str: continue # Ignora auto-loops no cálculo de desequilíbrio
        
        key = tuple(sorted((u_str, v_str)))
        p_e = data.get('positive_prob', 0.5)
        w_e = data.get('weight', 1.0)
        
        if key not in aggregated_edges:
            aggregated_edges[key] = {'pos': 0.0, 'neg': 0.0}
            
        aggregated_edges[key]['pos'] += w_e * p_e
        aggregated_edges[key]['neg'] += w_e * (1 - p_e)

    # --- 1. Define the fitness and individual structure ---
    if not hasattr(creator, "FitnessMulti"):
        creator.create("FitnessMulti", base.Fitness, weights=(-1.0, -1.0))
    if not hasattr(creator, "Individual"):
        creator.create("Individual", list, fitness=creator.FitnessMulti)

    # --- 2. Initialize the DEAP toolbox ---
    toolbox = base.Toolbox()

    int_to_node = {i: name for i, name in enumerate(nodes)}
    num_nodes = len(nodes)

    # --- 3. Register the Genetic Operators ---
    toolbox.register("attr_int", random.randint, 0, num_nodes - 1)
    toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_int, n=num_nodes)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Registra a função de avaliação com as arestas já agregadas
    toolbox.register("evaluate", evaluate_fitness, nodes_map=int_to_node, G=G, aggregated_edges=aggregated_edges)

    toolbox.register("mate", tools.cxTwoPoint) # Crossover
    toolbox.register("mutate", tools.mutUniformInt, low=0, up=num_nodes - 1, indpb=0.1) # Mutation
    toolbox.register("select", tools.selNSGA2) # Selection (NSGA-II)

    return toolbox


# --- Test Block ---
if __name__ == "__main__":
    print("--- Running test for evaluate_fitness function ---")

    # 1. Create a simple test graph
    G_test = nx.MultiGraph() 
    G_test.add_edge("A", "B", positive_prob=0.1, weight=1.0) 
    G_test.add_edge("B", "C", positive_prob=0.2, weight=1.0) 
    G_test.add_edge("A", "C", positive_prob=0.3, weight=1.0) 
    G_test.add_edge("C", "D", positive_prob=0.8, weight=1.0) 

    nodes = sorted(list(G_test.nodes()))
    int_to_node = {i: name for i, name in enumerate(nodes)}

    test_chromosome = [0, 0, 2, 2] # A&B, C&D

    f1, f2 = evaluate_fitness(test_chromosome, int_to_node, G_test)

    print(f"Test Graph nodes: {nodes}")
    print(f"Test Chromosome: {test_chromosome}")
    print(f"\nCalculated Fitness:")
    print(f"  - f1 (Disagreement): {f1:.4f}")
    print(f"  - f2 (Num_Clusters): {f2}")

    expected_f1 = (1 - 0.1) + (0.2) + (0.3) + (1 - 0.8) 
    print(f"\nManual check: Expected Disagreement should be {expected_f1:.4f}. -> {'OK' if abs(f1 - expected_f1) < 1e-9 else 'FAIL'}")

    print(f"\n--- Running Test for GA Toolbox Setup ---")
    toolbox = setup_genetic_algorithm(nodes, G_test)
    ind = toolbox.individual()
    
    print(f"Generated a sample individual (chromosome): {ind}")
    print(f"Length of chromosome is {len(ind)}, which should be {len(nodes)}. -> {'OK' if len(ind) == len(nodes) else 'FAIL'}")