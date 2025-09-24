# src/main.py
import argparse
import os
import pandas as pd
import time

from graph_constructor import build_multigraph_from_csv
from optimization_model import solve_multigraph_cc
from visualizer import visualize_and_save_graph

def print_cluster_summary(clusters: dict):
    print("\n--- Cluster Partition Summary ---")
    grouped_clusters = {}
    for node, cluster_id in clusters.items():
        grouped_clusters.setdefault(cluster_id, []).append(node)
    
    for cid in grouped_clusters:
        grouped_clusters[cid].sort()
        
    for cid, members in sorted(grouped_clusters.items()):
        print(f"Cluster represented by '{cid}': {members}")
    print("---------------------------------")

def main():
    parser = argparse.ArgumentParser(description="Solve the Multi-Objective Correlation Clustering problem for multigraphs.")
    
    parser.add_argument('--data', required=True, help="Path to the input .csv data file.")
    parser.add_argument('--output_dir', required=True, help="Directory to save results.")
    parser.add_argument('--time_limit', type=int, default=3600, help="Time limit in seconds for the optimization solver.")
    parser.add_argument(
        '--lambda_weight', 
        type=float, 
        default=0.5, 
        help="Lambda weight (0.0 to 1.0) for the weighted sum objective."
    )
    
    args = parser.parse_args()

    start_time = time.time()
    print("="*50 + f"\nSTARTING MULTI-OBJECTIVE ANALYSIS | {time.strftime('%Y-%m-%d %H:%M:%S')}\n" + "="*50)
    print(f"Input instance: {args.data}")
    print(f"Output directory: {args.output_dir}")
    print(f"Lambda Weight: {args.lambda_weight}")
    print(f"Time limit: {args.time_limit}s")
    print("="*50)

    G = build_multigraph_from_csv(args.data)
    if not G: return
    
    results = solve_multigraph_cc(G, lambda_weight=args.lambda_weight, time_limit=args.time_limit)
    if not results: return

    # Unpack the new return values
    clusters, obj_val, exec_time, f1_disagreement, f2_num_clusters = results
    
    print_cluster_summary(clusters)

    print("\nSaving results...")
    try:
        os.makedirs(args.output_dir, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(args.data))[0]
        # The stats file should be unique per lambda run, let's adjust its location
        # It will now be saved inside the specific output directory for that run
        stats_txt_path = os.path.join(args.output_dir, f"{base_name}_lambda_{args.lambda_weight}_stats.txt")
        result_prefix = f"{base_name}_lambda_{args.lambda_weight}"

        viz_path = os.path.join(args.output_dir, f"{result_prefix}_viz.png")
        visualize_and_save_graph(G, clusters, viz_path)
        
        clusters_csv_path = os.path.join(args.output_dir, f"{result_prefix}_clusters.csv")
        df_clusters = pd.DataFrame(list(clusters.items()), columns=['node', 'cluster_representative'])
        df_clusters.sort_values(by=['cluster_representative', 'node']).to_csv(clusters_csv_path, index=False)
        print(f"  - Cluster partition saved to: {clusters_csv_path}")
        
        total_time = time.time() - start_time
        with open(stats_txt_path, 'w') as f:
            f.write(f"--- Execution Statistics ---\n")
            f.write(f"Instance: {args.data}\n")
            f.write(f"Lambda_Weight: {args.lambda_weight}\n")
            f.write(f"Combined_Objective_Value_Z: {obj_val}\n")
            f.write(f"Disagreement_Value_f1: {f1_disagreement}\n")
            f.write(f"Num_Clusters_Value_f2: {int(f2_num_clusters)}\n")
            f.write(f"Solver_Execution_Time_s: {exec_time}\n")
            f.write(f"Total_Script_Time_s: {total_time}\n")
        print(f"  - Execution stats saved to: {stats_txt_path}")
    
    except Exception as e:
        print(f"An error occurred while saving results: {e}")
            
    print("\n--- ANALYSIS COMPLETE ---")

if __name__ == '__main__':
    main()