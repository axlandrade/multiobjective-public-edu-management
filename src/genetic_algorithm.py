# src/genetic_algorithm.py

import networkx as nx
from typing import List, Dict, Tuple

def evaluate_fitness(
    chromosome: List[int], 
    nodes_map: Dict[int, str], 
    G: nx.MultiGraph
) -> Tuple[float, int]:
    """
    [English]
    Calculates the fitness of a given chromosome based on two objectives:
    1. Expected disagreement (to be minimized).
    2. Number of clusters (to be minimized).

    Args:
        chromosome (List[int]): A list representing a partition. The index is the
                                node's integer ID, and the value is the integer ID
                                of its cluster representative.
        nodes_map (Dict[int, str]): A dictionary mapping integer IDs back to
                                    the original node names (e.g., {0: "I1", ...}).
        G (nx.MultiGraph): The multigraph of the network.

    Returns:
        Tuple[float, int]: A tuple containing the two fitness values:
                           (f1_disagreement, f2_num_clusters).

    ------------------------------------------------------------------------------------

    [Português]
    Calcula a aptidão (fitness) de um cromossomo dado com base em dois objetivos:
    1. Desequilíbrio esperado (a ser minimizado).
    2. Número de clusters (a ser minimizado).

    Argumentos:
        cromossomo (List[int]): Uma lista representando uma partição. O índice é o
                                ID inteiro do nó, e o valor é o ID inteiro do
                                seu representante de cluster.
        nodes_map (Dict[int, str]): Um dicionário que mapeia IDs inteiros de volta
                                    para os nomes originais dos nós (ex., {0: "I1", ...}).
        G (nx.MultiGraph): O multigrafo da rede.
        
    Retorna:
        Tuple[float, int]: Uma tupla contendo os dois valores de fitness:
                           (f1_desequilíbrio, f2_num_clusters).
    """

    # --- Step 1: Translate chromosome into a more usable partition map ---
    partition = {nodes_map[i]: nodes_map[chromosome[i]] for i in range(len(chromosome))}

    # --- Step 2: Calculate f1 (Expected Disagreement) ---
    disagreement = 0.0
    for u, v, data in G.edges(data=True):
        p_e = data['positive_prob']
        w_e = data['weight']

        is_same_cluster = (partition[u] == partition[v])

        if is_same_cluster:
            # [English] If in the same cluster, the disagreement cost is the probability of the edge being negative.
            # [Português] Se estiverem no mesmo cluster, o custo de discordância é a probabilidade da aresta ser negativa.
            disagreement += w_e * (1 - p_e)
        else:
            # [English] If in different clusters, the disagreement cost is the probability of the edge being positive.
            # [Português] Se estiverem em clusters diferentes, o custo de discordância é a probabilidade da aresta ser positiva.
            disagreement += w_e * p_e

    # --- Step 3: Calculate f2 (Number of Clusters) ---
    num_clusters = len(set(chromosome))

    return disagreement, num_clusters

# --- Test Block ---
if __name__ == "__main__":
    print("--- Running test for evaluate_fitness function ---")

    # 1. Create a simple test graph
    G_test = nx.Graph() # Usando nx.Graph para o teste simples para garantir uma aresta por par
    G_test.add_edge("A", "B", positive_prob=0.1, weight=1.0) # p < 0.5, should be separate
    G_test.add_edge("B", "C", positive_prob=0.2, weight=1.0) # p < 0.5, should be separate
    G_test.add_edge("A", "C", positive_prob=0.3, weight=1.0) # p < 0.5, should be separate
    G_test.add_edge("C", "D", positive_prob=0.8, weight=1.0) # p > 0.5, should be together

    nodes = sorted(list(G_test.nodes()))
    int_to_node = {i: name for i, name in enumerate(nodes)}

    # 2. Define a sample chromosome representing a partition
    # Partition: {A, B} and {C, D}
    # Nodes (alphabetical): A, B, C, D
    # Indices:              0, 1, 2, 3
    # Representatives:      A (idx 0), C (idx 2)
    test_chromosome = [0, 0, 2, 2] 

    # 3. Call the evaluation function
    f1, f2 = evaluate_fitness(test_chromosome, int_to_node, G_test)

    # 4. Print results
    print(f"Test Graph nodes: {nodes}")
    print(f"Test Chromosome: {test_chromosome}")
    print(f"  - Represents partition: A&B in cluster 'A', C&D in cluster 'C'")
    print(f"\nCalculated Fitness:")
    print(f"  - f1 (Disagreement): {f1}")
    print(f"  - f2 (Num_Clusters): {f2}")

    # --- CORREÇÃO APLICADA AQUI ---
    # Agora a verificação manual usa os valores corretos do grafo de teste
    expected_f1 = (1 - 0.1) + (0.2) + (0.3) + (1 - 0.8) # 0.9 + 0.2 + 0.3 + 0.2 = 1.6
    print(f"\nManual check: Expected Disagreement should be {expected_f1:.4f}. -> {'OK' if abs(f1 - expected_f1) < 1e-9 else 'FAIL'}")