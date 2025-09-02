# src/optimization_model.py

import networkx as nx
import gurobipy as gp
from gurobipy import GRB
from itertools import combinations

def solve_multigraph_cc(G: nx.MultiGraph, time_limit: int = 3600) -> tuple:
    """
    Solves the Probabilistic Correlation Clustering problem for a multigraph.
    """
    try:
        print("\nBuilding the optimization model...")
        
        model = gp.Model("correlation_clustering_multigraph")
        model.setParam('OutputFlag', 0) # Turns off Gurobi logs for cleaner output

        nodes = list(G.nodes())
        x = {}
        # BUG FIX: Use tuple(sorted(...)) to create consistent keys for variables
        for i, j in combinations(nodes, 2):
            key = tuple(sorted((i, j)))
            x[key] = model.addVar(vtype=GRB.BINARY, name=f"x_{key[0]}_{key[1]}")
        
        print(f"  - {len(x)} decision variables created.")

        objective = gp.LinExpr()
        for u, v, data in G.edges(data=True):
            p_e = data['positive_prob']
            w_e = data['weight']
            
            key = tuple(sorted((u, v)))
            var_x = x[key]
            
            objective += w_e * (p_e * var_x + (1 - p_e) * (1 - var_x))
            
        model.setObjective(objective, GRB.MINIMIZE)
        print("  - Objective function built.")

        constraint_count = 0
        # BUG FIX: The loop was (i, j, j), now it is (i, j, k)
        for i, j, k in combinations(nodes, 3):
            # BUG FIX: Use consistent keys to access variables
            key_ij = tuple(sorted((i, j)))
            key_jk = tuple(sorted((j, k)))
            key_ik = tuple(sorted((i, k)))
            
            model.addConstr(x[key_ij] + x[key_jk] >= x[key_ik])
            model.addConstr(x[key_ik] + x[key_jk] >= x[key_ij])
            model.addConstr(x[key_ij] + x[key_ik] >= x[key_jk])
            constraint_count += 3
        
        print(f"  - {constraint_count} triangular inequality constraints added.")

        model.setParam('TimeLimit', time_limit)
        print(f"\nStarting optimization with a time limit of {time_limit} seconds...")
        model.optimize()
        print("Optimization finished.")

        if model.Status == GRB.OPTIMAL or model.Status == GRB.TIME_LIMIT:
            objective_value = model.ObjVal
            execution_time = model.Runtime

            clusters = _reconstruct_clusters(nodes, x)
            
            print(f"  - Minimum expected imbalance: {objective_value:.4f}")
            print(f"  - Execution time: {execution_time:.2f}s")
            print(f"  - Number of clusters found: {len(set(clusters.values()))}")
            
            return clusters, objective_value, execution_time
        else:
            print(f"Could not find an optimal solution. Status code: {model.Status}")
            return None, None, None

    except gp.GurobiError as e:
        print(f"Gurobi error: {e.code} ({e.message})")
        return None, None, None
    except Exception as e:
        print(f"An unexpected error occurred during optimization: {e}")
        return None, None, None

def _reconstruct_clusters(nodes: list, x: dict) -> dict:
    """Helper function to convert the x_ij decision variables into a final partition."""
    cluster_graph = nx.Graph()
    cluster_graph.add_nodes_from(nodes)
    
    for key, var in x.items():
        if var.X < 0.5: # If x_ij is 0, nodes are in the same cluster
            cluster_graph.add_edge(key[0], key[1])
    
    connected_components = list(nx.connected_components(cluster_graph))
    
    cluster_map = {}
    for i, cluster in enumerate(connected_components):
        for node in cluster:
            cluster_map[node] = i
    
    return cluster_map