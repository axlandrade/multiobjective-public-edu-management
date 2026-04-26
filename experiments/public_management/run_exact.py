# experiments/public_management/run_exact.py
import argparse
import os
import pandas as pd
import time

# Importando as funções dos seus outros módulos
from create_real_network import main as create_real_network_main
from graph_constructor import build_multigraph_from_csv
from optimization_model import solve_multigraph_cc
from visualizer import visualize_and_save_graph

def print_cluster_summary(clusters: dict):
    """Imprime um resumo da partição de clusters encontrada."""
    print("\n--- Resumo da Partição de Clusters ---")
    grouped_clusters = {}
    for node, cluster_id in clusters.items():
        grouped_clusters.setdefault(cluster_id, []).append(node)
    
    # Ordena os membros de cada cluster para uma visualização consistente
    for cid in grouped_clusters:
        grouped_clusters[cid].sort()
        
    # Imprime os clusters ordenados pelo nome do representante
    for cid, members in sorted(grouped_clusters.items()):
        print(f"Cluster representado por '{cid}': {members}")
    print("---------------------------------------")

def main():
    parser = argparse.ArgumentParser(description="Executa o MODELO EXATO (PLI) nos dados reais.")
    
    parser.add_argument(
        '--lambda_weight', 
        type=float, 
        default=0.5, 
        help="Peso Lambda (entre 0.0 e 1.0) para a função objetivo ponderada."
    )
    parser.add_argument(
        '--time_limit', 
        type=int, 
        default=3600, # Padrão de 1 hora
        help="Limite de tempo em segundos para o solver de otimização."
    )
    
    args = parser.parse_args()

    # --- AVISO DE PERFORMANCE ---
    print("="*70)
    print("ATENÇÃO: EXECUTANDO O MODELO EXATO EM DADOS REAIS")
    print("="*70)
    print("Este script é destinado a testes de viabilidade em pequena escala.")
    print("Devido à complexidade computacional (O(N³)), é esperado que o solver")
    print(f"atinja o limite de tempo de {args.time_limit}s sem encontrar a solução ótima.")
    print("Para uma análise completa dos dados reais, a abordagem com Algoritmo Genético")
    print("(run_real.py) é a recomendada por sua escalabilidade.")
    print("="*70)
    
    # --- ETAPA 1: Preparar os dados da rede real ---
    print("\n--- Etapa 1: Preparando o arquivo da rede de dados reais ---")
    # Chama a função principal de create_real_network.py para garantir que o arquivo de entrada exista
    create_real_network_main()
    real_data_path = 'data/rede_real_input.csv'
    
    if not os.path.exists(real_data_path):
        print(f"ERRO: Não foi possível criar ou encontrar o arquivo '{real_data_path}'. Abortando.")
        return

    # --- ETAPA 2: Executar o modelo de otimização ---
    print("\n--- Etapa 2: Iniciando a otimização exata ---")
    start_time = time.time()
    
    G = build_multigraph_from_csv(real_data_path)
    if not G: return
    
    output_dir = f"results_exact_real/lambda_{args.lambda_weight}"
    
    # Chama o solver exato do seu módulo de otimização
    results = solve_multigraph_cc(G, lambda_weight=args.lambda_weight, time_limit=args.time_limit)
    if not results[0]:  # Verifica se o primeiro valor de retorno (clusters) é None
        print("\n--- ANÁLISE CONCLUÍDA (sem solução viável) ---")
        return

    clusters, obj_val, exec_time, f1_disagreement, f2_num_clusters = results
    
    print_cluster_summary(clusters)

    # --- ETAPA 3: Salvar os resultados ---
    print("\n--- Etapa 3: Salvando os resultados ---")
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        # Salva o particionamento dos clusters
        clusters_csv_path = os.path.join(output_dir, "clusters_encontrados.csv")
        df_clusters = pd.DataFrame(list(clusters.items()), columns=['node', 'cluster_representative'])
        df_clusters.sort_values(by=['cluster_representative', 'node']).to_csv(clusters_csv_path, index=False)
        print(f"  - Partição de clusters salva em: {clusters_csv_path}")
        
        # Salva as estatísticas da execução
        stats_txt_path = os.path.join(output_dir, "estatisticas_execucao.txt")
        total_time = time.time() - start_time
        with open(stats_txt_path, 'w') as f:
            f.write(f"--- Estatísticas da Execução (Modelo Exato em Dados Reais) ---\n")
            f.write(f"Arquivo de Entrada: {real_data_path}\n")
            f.write(f"Peso_Lambda: {args.lambda_weight}\n")
            f.write(f"Limite_de_Tempo_s: {args.time_limit}\n")
            f.write(f"Valor_Objetivo_Combinado_Z: {obj_val}\n")
            f.write(f"Valor_Desequilibrio_f1: {f1_disagreement}\n")
            f.write(f"Valor_Num_Clusters_f2: {int(f2_num_clusters)}\n")
            f.write(f"Tempo_Execucao_Solver_s: {exec_time}\n")
            f.write(f"Tempo_Total_Script_s: {total_time}\n")
        print(f"  - Estatísticas da execução salvas em: {stats_txt_path}")
    
    except Exception as e:
        print(f"Ocorreu um erro ao salvar os resultados: {e}")
            
    print("\n--- ANÁLISE COMPLETA ---")

if __name__ == '__main__':
    main()