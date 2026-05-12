"""Exact OR-Tools model for public-management correlation clustering.

The model uses representative variables: each node is assigned to one cluster
representative, and the objective balances expected disagreement (f1) against
the number of clusters (f2) through a weighted sum controlled by lambda_weight.
"""

import time
import networkx as nx
from ortools.linear_solver import pywraplp

def solve_multigraph_cc(G: nx.MultiGraph, lambda_weight: float = 0.5, time_limit: int = 3600):
    """
    Resolve o modelo exato para Correlation Clustering em Multigrafos (Gestão Pública)
    usando o Google OR-Tools. Retorna a partição de clusters e as estatísticas.
    """
    start_time = time.time()
    
    # 1. Instancia o solver exato (SCIP é muito bom para PLI dentro do OR-Tools)
    # SCIP is the mixed-integer solver used through OR-Tools.
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        print("ERRO: Solver SCIP não disponível no OR-Tools atual.")
        return None, None, None, None, None
        
    solver.SetTimeLimit(time_limit * 1000)  # O limite no OR-Tools é em milissegundos
    
    nodes = list(G.nodes())
    N = len(nodes)
    
    # Dicionário reverso para facilitar a busca do índice
    node_to_idx = {node: i for i, node in enumerate(nodes)}

    # Pré-cálculo das probabilidades (pesos) P+ e P- para cada par de vértices
    # f1 = sum_{i<j} ( P- * s_ij + P+ * (1 - s_ij) )
    P_plus = {}
    P_minus = {}
    
    # w and s transform the nonlinear statement "i and j are in the same
    # cluster" into linear constraints that SCIP can optimize.
    for i in range(N):
        for j in range(i+1, N):
            u = nodes[i]
            v = nodes[j]
            p_plus = 0.0
            p_minus = 0.0
            
            # Se existe aresta no multigrafo entre u e v
            if G.has_edge(u, v):
                # Soma os pesos das múltiplas arestas (índices de risco / probabilidades)
                for key in G[u][v]:
                    edge_data = G[u][v][key]
                    peso = edge_data.get('weight', 0.5)
                    # Exemplo: probabilidade de corrupção (p_plus) vs probabilidade de honestidade (p_minus)
                    p_plus += peso
                    p_minus += (1.0 - peso)
                    
            P_plus[(i, j)] = p_plus
            P_minus[(i, j)] = p_minus

    # ---------------------------------------------------------
    # 2. VARIÁVEIS DE DECISÃO
    # ---------------------------------------------------------
    # y[i] = 1 se o vértice i é um representante de cluster
    y = {}
    for i in range(N):
        y[i] = solver.IntVar(0, 1, f'y_{i}')
        
    # z[i,j] = 1 se o vértice j pertence ao cluster representado pelo vértice i
    z = {}
    for i in range(N):
        for j in range(N):
            z[i, j] = solver.IntVar(0, 1, f'z_{i}_{j}')
            
    # w[i,j,k] = 1 se i e j pertencem simultaneamente ao cluster representado por k (i < j)
    w = {}
    for i in range(N):
        for j in range(i+1, N):
            for k in range(N):
                w[i, j, k] = solver.IntVar(0, 1, f'w_{i}_{j}_{k}')
                
    # s[i,j] = 1 se i e j pertencem a QUALQUER cluster em comum (i < j)
    s = {}
    for i in range(N):
        for j in range(i+1, N):
            s[i, j] = solver.IntVar(0, 1, f's_{i}_{j}')

    # ---------------------------------------------------------
    # 3. RESTRIÇÕES ESTRUTURAIS
    # ---------------------------------------------------------
    for j in range(N):
        # Alocação única: cada nó j pertence a exatamente 1 representante i
        solver.Add(sum(z[i, j] for i in range(N)) == 1)
        
    for i in range(N):
        # Auto-alocação do representante: z[i,i] == y[i]
        solver.Add(z[i, i] == y[i])
        for j in range(N):
            # Consistência: z[i,j] <= y[i]
            solver.Add(z[i, j] <= y[i])

    # ---------------------------------------------------------
    # 4. RESTRIÇÕES DE LINEARIZAÇÃO 
    # ---------------------------------------------------------
    for i in range(N):
        for j in range(i+1, N):
            for k in range(N):
                solver.Add(w[i, j, k] <= z[k, i])
                solver.Add(w[i, j, k] <= z[k, j])
                solver.Add(w[i, j, k] >= z[k, i] + z[k, j] - 1)
                
            # s[i,j] = soma dos w[i,j,k]
            solver.Add(s[i, j] == sum(w[i, j, k] for k in range(N)))

    # ---------------------------------------------------------
    # 5. FUNÇÕES OBJETIVO
    # ---------------------------------------------------------
    # F2: Número de Clusters
    f2_expr = sum(y[i] for i in range(N))
    
    # F1: Desequilíbrio Esperado
    # f1 = sum_{i<j} ( P- * s_ij + P+ * (1 - s_ij) )
    f1_expr = sum(
        P_minus[(i, j)] * s[i, j] + P_plus[(i, j)] * (1 - s[i, j])
        for i in range(N) for j in range(i+1, N)
    )

    # Objeivo Combinado (Soma Ponderada)
    # Lembrete: Se F1 e F2 estiverem em escalas muito diferentes, o ideal é normalizar.
    # Neste script padrão mantemos a formulação bruta Z = lambda * F1 + (1 - lambda) * F2
    # Combined weighted-sum objective.
    Z = lambda_weight * f1_expr + (1.0 - lambda_weight) * f2_expr
    
    solver.Minimize(Z)

    # ---------------------------------------------------------
    # 6. RESOLUÇÃO E EXTRAÇÃO DE RESULTADOS
    # ---------------------------------------------------------
    status = solver.Solve()
    
    exec_time = time.time() - start_time
    
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        # Extrair a partição de clusters
        clusters = {}
        for j in range(N):
            for i in range(N):
                if z[i, j].solution_value() > 0.5:
                    node_name = nodes[j]
                    repr_name = nodes[i]
                    clusters[node_name] = repr_name
                    break
        
        # Calcular os valores reais das funções
        obj_val = solver.Objective().Value()
        f2_val = sum(y[i].solution_value() for i in range(N))
        
        f1_val = sum(
            P_minus[(i, j)] * s[i, j].solution_value() + P_plus[(i, j)] * (1 - s[i, j].solution_value())
            for i in range(N) for j in range(i+1, N)
        )
        
        return clusters, obj_val, exec_time, f1_val, f2_val
    else:
        # Solver não encontrou nem solução viável no tempo limite
        return None, None, exec_time, None, None
