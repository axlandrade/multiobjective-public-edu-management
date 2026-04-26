# src/optimization_model.py

from itertools import combinations
from gurobipy import GRB
import networkx as nx
import gurobipy as gp

options = {
    "WLSACCESSID": "00ae781a-b0e8-40c0-b592-fbb33def1fbe",
    "WLSSECRET": "4f93872a-59ef-4057-93f6-8600037f94a5",
    "LICENSEID": 2718197,
}
with gp.Env(params=options) as env, gp.Model(env=env) as model:
    pass  # Apenas para inicializar o ambiente Gurobi com as opções fornecidas


def solve_multigraph_cc(G: nx.MultiGraph, lambda_weight: float = 0.5, time_limit: int = 3600) -> tuple:
    """
    [Português]
    Resolve o problema de Correlation Clustering Probabilístico Multiobjetivo.

    Retorna:
        Uma tupla contendo:
        - dict: Mapeamento de cada nó ao seu representante de cluster.
        - float: Valor final da função objetivo combinada (Z).
        - float: Tempo computacional gasto pelo solver.
        - float: Valor final do objetivo de desequilíbrio (f1).
        - int: Valor final do objetivo de número de clusters (f2).
    """
    try:
        print("\nBuilding the multi-objective optimization model...")

        model = gp.Model("multi_objective_cc")
        # Mudei para 1 para vermos o progresso do Gurobi
        model.setParam('OutputFlag', 1)

        # --- CORREÇÃO: Garantir que todos os nós são strings ---
        nodes = sorted([str(n) for n in G.nodes()])
        # --- FIM DA CORREÇÃO ---

        # --- STAGE 1: Decision Variables ---
        y = model.addVars(nodes, vtype=GRB.BINARY, name="y")
        z = model.addVars(nodes, nodes, vtype=GRB.BINARY, name="z")

        print(f"  - Created {len(y)} representative variables ('y').")
        print(f"  - Created {len(z)} assignment variables ('z').")

        # --- STAGE 2: Structural Constraints ---
        for j in nodes:
            model.addConstr(gp.quicksum(z[i, j]
                            for i in nodes) == 1, name=f"assign_{j}")

        for i in nodes:
            model.addConstr(z[i, i] == y[i], name=f"self_assign_{i}")
            for j in nodes:
                if i != j:
                    model.addConstr(z[i, j] <= y[i],
                                    name=f"consistency_{i}_{j}")

        print("  - Added structural constraints for the representative model.")

        # --- STAGE 3: Linearization Variables and Constraints ---
        # Usando 'combinations' com a lista de nós já convertida para string
        node_pairs = list(combinations(nodes, 2))
        w = model.addVars(node_pairs, nodes, vtype=GRB.BINARY, name="w")
        s = model.addVars(node_pairs, vtype=GRB.BINARY, name="s")

        for a, b in s.keys():
            model.addConstr(s[a, b] == gp.quicksum(w[a, b, k]
                            for k in nodes), name=f"s_def_{a}_{b}")

            for k in nodes:
                model.addConstr(w[a, b, k] <= z[k, a],
                                name=f"w_lin1_{a}_{b}_{k}")
                model.addConstr(w[a, b, k] <= z[k, b],
                                name=f"w_lin2_{a}_{b}_{k}")
                model.addConstr(w[a, b, k] >= z[k, a] +
                                z[k, b] - 1, name=f"w_lin3_{a}_{b}_{k}")

        print("  - Added linearization constraints.")

        # --- STAGE 4: Multi-Objective Function (Weighted Sum) ---
        f1_disagreement = gp.LinExpr()
        for u, v, data in G.edges(data=True):
            # --- CORREÇÃO: Garantir que as chaves também são strings ---
            u_str, v_str = str(u), str(v)
            key = tuple(sorted((u_str, v_str)))
            # --- FIM DA CORREÇÃO ---

            # Checa se a chave existe (caso u == v)
            if key in s:
                p_e = data['positive_prob']
                w_e = data['weight']
                f1_disagreement += w_e * \
                    (p_e * (1 - s[key]) + (1 - p_e) * s[key])

        f2_num_clusters = gp.quicksum(y[i] for i in nodes)

        # Normalização dos objetivos
        N = len(nodes)
        W_total = sum(d['weight'] for _, _, d in G.edges(data=True))

        f1_norm = f1_disagreement / W_total if W_total > 0 else 0
        f2_norm = f2_num_clusters / N if N > 0 else 0

        lambda_val = lambda_weight
        model.setObjective(lambda_val * f1_norm +
                           (1 - lambda_val) * f2_norm, GRB.MINIMIZE)

        print("  - Multi-objective function built.")

        # --- STAGE 5: Optimize and Process Results ---
        model.setParam('TimeLimit', time_limit)
        print(
            f"\nStarting optimization with lambda = {lambda_val} and time limit = {time_limit}s...")
        model.optimize()
        print("Optimization finished.")

        if model.Status in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
            clusters = _reconstruct_clusters_from_representatives(nodes, z)

            # Capture the final values of the individual objectives
            final_f1 = f1_disagreement.getValue()
            final_f2 = f2_num_clusters.getValue()

            print(f"\n--- Optimization Results ---")
            print(
                f"  - Combined Normalized Objective Value (Z): {model.ObjVal:.4f}")
            print(f"  - Disagreement (f1): {final_f1:.4f}")
            print(f"  - Number of Clusters (f2): {int(final_f2)}")
            print(f"  - Solver Execution Time: {model.Runtime:.2f}s")

            return clusters, model.ObjVal, model.Runtime, final_f1, final_f2
        else:
            print(
                f"Could not find a viable solution. Status code: {model.Status}")
            return None, None, None, None, None

    except gp.GurobiError as e:
        print(f"A Gurobi error occurred: {e}")
        return None, None, None, None, None
    except Exception as e:
        print(f"An unexpected error occurred during optimization: {e}")
        return None, None, None, None, None


def _reconstruct_clusters_from_representatives(nodes: list, z: dict) -> dict:
    cluster_map = {}

    # Acessa as chaves do Gurobi Var corretamente
    representatives = {i for i in nodes if z[i, i].X > 0.5}

    for j in nodes:
        for i in representatives:
            if z[i, j].X > 0.5:
                cluster_map[j] = i
                break
    return cluster_map
