import os
import ast
import json
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

# Usaremos um algoritmo rápido de Correlação (Pivot/KwikCluster)
# para não precisar chamar o Gurobi para agrupar 967 nós!
def kwik_cluster(nodes, pos_edges, neg_edges):
    """
    Algoritmo 3-aproximado rápido para Correlation Clustering (Ailon et al., 2005)
    Ideal para agrupar centenas de soluções em segundos.
    """
    V = set(nodes)
    clusters = []
    
    # Cria grafos de adjacência rápidos
    adj_pos = {u: set() for u in V}
    for u, v in pos_edges:
        adj_pos[u].add(v)
        adj_pos[v].add(u)
        
    while V:
        # 1. Escolhe um pivô aleatório
        pivot = V.pop()
        
        # 2. O cluster é o pivô + todos os amigos positivos dele
        cluster = {pivot}
        amigos = adj_pos[pivot].intersection(V)
        
        cluster.update(amigos)
        V.difference_update(amigos)
        
        clusters.append(list(cluster))
        
    return clusters

def main():
    print("="*60)
    print("AGRUPANDO A FRONTEIRA DE PARETO (CORRELATION CLUSTERING)")
    print("="*60)

    # --- 1. Carregar a Fronteira ---
    csv_path = 'results_edu/pareto_nsga2_wsac_wsms.csv'
    if not os.path.exists(csv_path):
        print(f"Erro: Arquivo {csv_path} não encontrado. Rode o run_heuristic.py primeiro!")
        return
        
    df = pd.read_csv(csv_path)
    
    # Vamos pegar apenas os perfis únicos de trade-off (F1, F2) para não ter nós repetidos idênticos
    # Isso acelera o grafo e limpa as 967 para as ~51 "Reais" 
    df_unique = df.drop_duplicates(subset=['f1_alunos', 'f2_custo_ru']).reset_index(drop=True)
    
    nodes = df_unique.index.tolist()
    print(f"Total de Soluções Únicas (Nós do Grafo): {len(nodes)}\n")

    # Converter string "[12, 4, -1]" de volta para lista de ints
    cromossomos = [ast.literal_eval(c) for c in df_unique['cromossomo']]
    
    # --- 2. Construir o Grafo de Sinais ---
    # Nós = Soluções. Aresta Positiva se forem 70%+ idênticas. Negativa caso contrário.
    pos_edges = []
    neg_edges = []
    LIMIAR_SIMILARIDADE = 0.65  # Se 65% das disciplinas caírem no mesmo dia/turno
    
    print("Construindo Grafo de Similaridade Gerencial...")
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            # Compara cromossomo I e J
            c1 = cromossomos[i]
            c2 = cromossomos[j]
            
            # Conta quantas disciplinas estão rigorosamente no mesmo slot
            iguais = sum(1 for a, b in zip(c1, c2) if a == b)
            taxa_similaridade = iguais / len(c1)
            
            if taxa_similaridade >= LIMIAR_SIMILARIDADE:
                pos_edges.append((i, j))
            else:
                neg_edges.append((i, j))
                
    print(f"Arestas Positivas (Acordos): {len(pos_edges)}")
    print(f"Arestas Negativas (Desacordos): {len(neg_edges)}\n")

    # --- 3. Rodar o Correlation Clustering ---
    print("Executando KwikCluster (Ailon et al.)...")
    np.random.seed(42) # Reprodutibilidade
    clusters = kwik_cluster(nodes, pos_edges, neg_edges)
    
    print(f"--> O algoritmo encontrou {len(clusters)} 'Perfis de Gestão' distintos!\n")

    # --- 4. Análise dos Perfis ---
    perfis_data = []
    for c_id, cluster_nodes in enumerate(clusters):
        # Pega as métricas F1 e F2 médias desse cluster
        df_cluster = df_unique.iloc[cluster_nodes]
        media_alunos = df_cluster['f1_alunos'].mean()
        media_custo = df_cluster['f2_custo_ru'].mean()
        min_custo = df_cluster['f2_custo_ru'].min()
        max_alunos = df_cluster['f1_alunos'].max()
        
        # Determinar o "nome" do perfil logicamente
        if media_alunos > 880:
            nome = "EXPANSIVO (Foco no Aluno)"
        elif media_custo < 4000:
            nome = "AUSTERIDADE (Foco no Orçamento)"
        elif 4000 <= media_custo <= 4800:
            nome = "EQUILÍBRIO CONSERVADOR"
        else:
            nome = "EQUILÍBRIO CUSTOSO"

        print(f"Cluster {c_id+1}: {nome}")
        print(f"  - Qtd de Grades: {len(cluster_nodes)}")
        print(f"  - Alunos Médios: {media_alunos:.1f} (Máx: {max_alunos})")
        print(f"  - Custo RU Médio: R$ {media_custo:.2f} (Min: R$ {min_custo:.2f})\n")
        
        for n in cluster_nodes:
            perfis_data.append({
                'sol_id': df_unique.iloc[n]['sol_id'],
                'cluster_id': c_id + 1,
                'perfil': nome,
                'f1_alunos': df_unique.iloc[n]['f1_alunos'],
                'f2_custo_ru': df_unique.iloc[n]['f2_custo_ru']
            })

    # --- 5. Exportar o Relatório Executivo ---
    df_perfis = pd.DataFrame(perfis_data).sort_values(by='f1_alunos')
    df_perfis.to_csv('results_edu/relatorio_reitor_clusters.csv', index=False)
    
    print("Salvo em 'results_edu/relatorio_reitor_clusters.csv'!")

if __name__ == "__main__":
    main()