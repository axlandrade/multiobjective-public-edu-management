# src/optimization_model.py

import networkx as nx
import gurobipy as gp
from gurobipy import GRB
from itertools import combinations

def solve_multigraph_cc(G: nx.MultiGraph, lambda_weight: float = 0.5, time_limit: int = 3600) -> tuple:
    """
    [English]
    Solves the Multi-Objective Probabilistic Correlation Clustering problem
    for a multigraph using the representative formulation and a weighted sum approach.

    Args:
        G: The input multigraph. Edges must have 'positive_prob' and 'weight'.
        lambda_weight: The weight (lambda) for the objective function, balancing
                       disagreement (lambda) vs. number of clusters (1-lambda).
        time_limit: The maximum time in seconds for the solver.

    Returns:
        A tuple containing:
        - dict: A dictionary mapping each node to its cluster representative.
        - float: The final combined objective function value.
        - float: The computation time spent by the solver.
    
    ------------------------------------------------------------------------------------

    [Português]
    Resolve o problema de Correlation Clustering Probabilístico Multiobjetivo
    para um multigrafo, usando a formulação por representantes e a abordagem de soma ponderada.

    Argumentos:
        G: O multigrafo de entrada. As arestas devem ter os atributos 'positive_prob' e 'weight'.
        lambda_weight: O peso (lambda) para a função objetivo, que balanceia o 
                       desequilíbrio (lambda) vs. o número de clusters (1-lambda).
        time_limit: O tempo máximo em segundos para a execução do solver.

    Retorna:
        Uma tupla contendo:
        - dict: Um dicionário que mapeia cada nó ao seu representante de cluster.
        - float: O valor final da função objetivo combinada.
        - float: O tempo computacional gasto pelo solver.
    """
    try:
        print("\nBuilding the multi-objective optimization model...")
        
        model = gp.Model("multi_objective_cc")
        model.setParam('OutputFlag', 0)

        nodes = list(G.nodes())

        # --- STAGE 1: Decision Variables ---
        # y_i = 1 if node i is a cluster representative
        y = model.addVars(nodes, vtype=GRB.BINARY, name="y")
        # z_ij = 1 if node j is assigned to the cluster represented by i
        z = model.addVars(nodes, nodes, vtype=GRB.BINARY, name="z")
        
        print(f"  - Created {len(y)} representative variables ('y').")
        print(f"  - Created {len(z)} assignment variables ('z').")

        # --- STAGE 2: Structural Constraints ---
        for j in nodes:
            # Each node must be assigned to exactly one representative
            model.addConstr(gp.quicksum(z[i, j] for i in nodes) == 1, name=f"assign_{j}")

        for i in nodes:
            # A representative must be assigned to itself
            model.addConstr(z[i, i] == y[i], name=f"self_assign_{i}")
            for j in nodes:
                # A node can only be assigned to an active representative
                if i != j:
                    model.addConstr(z[i, j] <= y[i], name=f"consistency_{i}_{j}")

        print("  - Added structural constraints for the representative model.")

        # --- STAGE 3: Linearization Variables and Constraints ---
        # w_abk = 1 if nodes 'a' and 'b' are BOTH in the cluster of 'k'
        w = model.addVars(combinations(nodes, 2), nodes, vtype=GRB.BINARY, name="w")
        # s_ab = 1 if nodes 'a' and 'b' are in the SAME cluster (any cluster)
        s = model.addVars(combinations(nodes, 2), vtype=GRB.BINARY, name="s")

        for a, b in s.keys():
            # Link 's' to 'w'
            model.addConstr(s[a, b] == gp.quicksum(w[a, b, k] for k in nodes), name=f"s_def_{a}_{b}")
            
            for k in nodes:
                # Linearization constraints to define 'w' based on 'z'
                model.addConstr(w[a, b, k] <= z[k, a], name=f"w_lin1_{a}_{b}_{k}")
                model.addConstr(w[a, b, k] <= z[k, b], name=f"w_lin2_{a}_{b}_{k}")
                model.addConstr(w[a, b, k] >= z[k, a] + z[k, b] - 1, name=f"w_lin3_{a}_{b}_{k}")

        print("  - Added linearization constraints.")

        # --- STAGE 4: Multi-Objective Function (Weighted Sum) ---
        # Objective 1: Minimize expected disagreement (f1)
        f1_disagreement = gp.LinExpr()
        for u, v, data in G.edges(data=True):
            p_e = data['positive_prob']
            w_e = data['weight']
            key = tuple(sorted((u, v)))
            
            # (1 - s_ab) is 1 if they are in DIFFERENT clusters
            # s_ab is 1 if they are in the SAME cluster
            f1_disagreement += w_e * (p_e * (1 - s[key]) + (1 - p_e) * s[key])

        # Objective 2: Minimize number of clusters (f2)
        f2_num_clusters = gp.quicksum(y[i] for i in nodes)
        
        # NOTE: For a rigorous academic paper, f1 and f2 should be normalized before combining.
        # For this implementation, we use a direct weighted sum as a strong starting point.
        lambda_val = lambda_weight
        model.setObjective(lambda_val * f1_disagreement + (1 - lambda_val) * f2_num_clusters, GRB.MINIMIZE)
        
        print("  - Multi-objective function built.")

        # --- STAGE 5: Optimize and Process Results ---
        model.setParam('TimeLimit', time_limit)
        print(f"\nStarting optimization with lambda = {lambda_val} and time limit = {time_limit}s...")
        model.optimize()
        print("Optimization finished.")

        if model.Status in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
            clusters = _reconstruct_clusters_from_representatives(nodes, z)
            
            print(f"\n--- Optimization Results ---")
            print(f"  - Combined Objective Value: {model.ObjVal:.4f}")
            print(f"  - Solver Execution Time: {model.Runtime:.2f}s")
            print(f"  - Number of Clusters Found: {len(set(clusters.values()))}")
            
            return clusters, model.ObjVal, model.Runtime
        else:
            print(f"Could not find an optimal solution. Status code: {model.Status}")
            return None, None, None

    except Exception as e:
        print(f"An unexpected error occurred during optimization: {e}")
        return None, None, None

def _reconstruct_clusters_from_representatives(nodes: list, z: dict) -> dict:
    """
    [English]
    Helper function to convert the z_ij decision variables into a final partition,
    mapping each node to its representative's ID.

    [Português]
    Função auxiliar para converter as variáveis de decisão z_ij na partição final,
    mapeando cada nó ao ID do seu representante.
    """
    cluster_map = {}
    # Find all nodes that are representatives (y_i = 1, which means z_ii = 1)
    representatives = {i for i, j in z.keys() if i == j and z[i,j].X > 0.5}

    for j in nodes:
        for i in representatives:
            # For each node 'j', find the representative 'i' it was assigned to
            if z[i, j].X > 0.5:
                cluster_map[j] = i
                break
    return cluster_map