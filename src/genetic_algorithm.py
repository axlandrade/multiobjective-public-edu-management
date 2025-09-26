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
        chromosome (List[int]): A list representing a partition. The index is the node's integer ID, and the value is the integer ID of its cluster representative.
        nodes_map(Dict[int, str]): A dictionary mapping integer IDs back to the original node names (e.g., {0: "I1", ...}).
        G (nx.Multigraph): The multigraph of the network.

    Returns:
        Tuple[float, int]: A tuple containing the two fitness values: (f1_disagreement), f2_num_clusters).

    ---------------------------------------------------------------------------------------------------------------------------------------------------------------------

    [Português]
    Calcula a aptidão de um cromossomo dado com base em dois objetivos:
    1. Discordância esperada (a ser minimizada).
    2. Número de clusters (a ser minimizado).

    Args:
        chromosome (List[int]): Uma lista representando uma partição. O índice é o ID inteiro do nó, e o valor é o ID inteiro de seu representante de cluster.
        nodes_map(Dict[int, str]): Um dicionário que mapeia IDs inteiros de volta para os nomes originais dos nós (ex., {0: "I1", ...}).
        G (nx.Multigraph): O multigrafo da rede.
    """

    # --- Step 1: Translate chromosome into a more usable partition map ---
    # [English] Map nodes to their respresentative's name.
    # [Português] Mapeia os nomes dos nós para o nome de seus representantes.
    partition = {nodes_map[i]: nodes_map[chromosome[i]] for i in range(len(chromosome))}

    # --- Step 2: Calculate f1 (expected disagreement) ---
    disagreement = 0.0
    for u, v, data in G.edges(data=True):
        p_e = data['positive_prob']
        w_e = data['weight']

        # Check if nodes u and v are in the same cluster
        is_same_cluster = (partition[u] == partition[v])

        if is_same_cluster:
            # [English] If in the same cluster. the disagreement cost is the probability of the edge being negative.
            # [Português] Se estiverem no mesmo cluster, o custo de discordância é a probabilidade da aresta ser negativa.
            disagreement += (1 - p_e) * w_e
        else:
            # [English] If in different clusters, the disagreement cost is the probability of the edge being positive.
            # [Português] Se estiverem em clusters diferentes, o custo de discordância é a probabilidade da aresta ser positiva.
            disagreement += p_e * w_e

    # --- Step 3: Calculte f2 (Number of Clusters) ---
    # [English] The number of clusters is the number of unique representatives in the chromosome.
    # [Português] O número de clusters é o número de representantes únicos no cromossomo.
    num_clusters = len(set(chromosome))

    return disagreement, num_clusters

# --- Test Block ---
if __name__ == "__main__":
    # [English] This block allow us to test the function directly.
    # [Português] Este bloco permite testar a função diretamente.

    print("--- Running test for evaluate_fitness function ---")

    # 1. Create a simple test graph
    G_test = nx.MultiGraph()
    G_test.add_edge("A", "B", positive_prob=0.1, weight=1.0) # Should be together
    G_test.add_edge("B", "C", positive_prob=0.2, weight=1.0) # Should be separate
    G_test.add_edge("A", "C", positive_prob=0.3, weight=1.0) # Should be separate
    G_test.add_edge("C", "D", positive_prob=0.8, weight=1.0) # Should be together

    nodes = list(G_test.nodes())
    node_to_int = {name: i for i, name in enumerate(nodes)}
    int_to_node = {i: name for i, name in enumerate(nodes)}

    # 2. Define a sample chromosome representing a partition
    # Partition: {A, B} and {C, D}
    # Representative of {A, B} is A (0), representative of {C, D} is C (2)
    # Chromosome values are the indices of the representatives.
    # Nodes: A, B, C, D
    # Indices: 0, 1, 2, 3
    test_chromosome = [0, 0, 2, 2] # A and B in cluster 0, C and D in cluster 2

    # 3. Call the evaluation function
    f1, f2 = evaluate_fitness(test_chromosome, int_to_node, G_test)

    # 4. Print results
    print(f"Test Graph nodes: {nodes}")
    print(f"Test Chromosome: {test_chromosome}")
    print(f" - Represents partition: A&B in cluster 'A', C&D in cluster 'C'")
    print(f"\nCalculated Fitness:")
    print(f" - Expected Disagreement (f1): {f1}")
    print(f" - Number of Clusters (f2): {f2}")

    # Expected Disagreement Calculation:
    # Edge (A, B): Same cluster; Cost = 1 - 0.9 = 0.1
    # Edge (B, C): Different clusters; Cost = 0.2
    # Edge (A, C): Different clusters; Cost = 0.3
    # Edge (C, D): Same cluster; Cost = 1 - 0.8 = 0.2
    # Total Expected Disagreement = 0.1 + 0.2 + 0.3 + 0.2 = 0.8
    print(f"\nManual Check: Expected Disagreement should be 0.8")