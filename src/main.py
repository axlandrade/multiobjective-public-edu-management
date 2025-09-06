# src/main.py
import argparse
import os
import pandas as pd
from datetime import datetime
import time

# Import our custom modules
from graph_constructor import build_multigraph_from_csv
from optimization_model import solve_multigraph_cc
from visualizer import visualize_and_save_graph

def print_cluster_summary(clusters: dict):
    """
    [English] Prints a user-friendly summary of the found clusters.
    [Português] Imprime um resumo amigável dos clusters encontrados.
    """
    print("\n--- Cluster Partition Summary ---")
    grouped_clusters = {}
    for node, cluster_id in clusters.items():
        # The cluster_id is the representative's ID
        grouped_clusters.setdefault(cluster_id, []).append(node)
    
    for cid in grouped_clusters:
        grouped_clusters[cid].sort()
        
    for cid, members in sorted(grouped_clusters.items()):
        print(f"Cluster represented by '{cid}': {members}")
    print("---------------------------------")


def main():
    """
    [English] 
    Main entry point for the multi-objective corruption network analysis pipeline.
    Orchestrates data loading, model solving, and saving the results.
    
    [Português]
    Ponto de entrada principal para o pipeline de análise multiobjetivo de redes de corrupção.
    Orquestra o carregamento de dados, a resolução do modelo e o salvamento dos resultados.
    """
    parser = argparse.ArgumentParser(description="Solve the Multi-Objective Correlation Clustering problem for multigraphs.")
    
    parser.add_argument('--data', required=True, help="Path to the input .csv data file.")
    parser.add_argument('--output_dir', required=True, help="Directory to save results.")
    parser.add_argument('--time_limit', type=int, default=3600, help="Time limit in seconds for the optimization solver.")
    
    # NEW ARGUMENT FOR LAMBDA
    parser.add_argument(
        '--lambda_weight', 
        type=float, 
        default=0.5, 
        help="Lambda weight (0.0 to 1.0) for the weighted sum objective. 1.0 focuses purely on disagreement, 0.0 on minimizing clusters."
    )
    
    args = parser.parse_args()

    start_time = time.time()
    print("="*50 + f"\nSTARTING MULTI-OBJECTIVE ANALYSIS | {time.strftime('%Y-%m-%d %H:%M:%S')}\n" + "="*50)
    print(f"Input instance: {args.data}")
    print(f"Output directory: {args.output_dir}")
    print(f"Lambda Weight: {args.lambda_weight}") # Display the lambda value
    print(f"Time limit: {args.time_limit}s")
    print("="*50)

    G = build_multigraph_from_csv(args.data)
    if not G: return
    
    # Pass the new lambda_weight argument to the solver function
    results = solve_multigraph_cc(G, lambda_weight=args.lambda_weight, time_limit=args.time_limit)
    if not results: return

    clusters, obj_val, exec_time = results
    
    print_cluster_summary(clusters)

    print("\nSaving results...")
    try:
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Modify the base name to include the lambda value for unique results
        base_name = os.path.splitext(os.path.basename(args.data))[0]
        result_prefix = f"{base_name}_lambda_{args.lambda_weight}"

        # Save visualization
        viz_path = os.path.join(args.output_dir, f"{result_prefix}_viz.png")
        visualize_and_save_graph(G, clusters, viz_path)
        
        # Save cluster partition
        clusters_csv_path = os.path.join(args.output_dir, f"{result_prefix}_clusters.csv")
        df_clusters = pd.DataFrame(list(clusters.items()), columns=['node', 'cluster_representative'])
        df_clusters.sort_values(by=['cluster_representative', 'node']).to_csv(clusters_csv_path, index=False)
        print(f"  - Cluster partition saved to: {clusters_csv_path}")
        
        # Save execution statistics
        total_time = time.time() - start_time
        stats_txt_path = os.path.join(args.output_dir, f"{result_prefix}_stats.txt")
        with open(stats_txt_path, 'w') as f:
            f.write(f"--- Execution Statistics ---\n")
            f.write(f"Instance: {args.data}\n")
            f.write(f"Lambda Weight: {args.lambda_weight}\n")
            f.write(f"Combined Objective Value: {obj_val}\n")
            f.write(f"Solver Execution Time (s): {exec_time}\n")
            f.write(f"Total Script Time (s): {total_time}\n")
            f.write(f"Number of Clusters Found: {len(set(clusters.values()))}\n")
        print(f"  - Execution stats saved to: {stats_txt_path}")
    
    except Exception as e:
        print(f"An error occurred while saving results: {e}")
            
    print("\n--- ANALYSIS COMPLETE ---")

if __name__ == '__main__':
    main()