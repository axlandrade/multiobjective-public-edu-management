# src/main.py

import argparse
import os
import pandas as pd
from datetime import datetime

# Import our functions
from graph_constructor import build_multigraph_from_csv
from optimization_model import solve_multigraph_cc
from visualizer import visualize_and_save_graph # <-- Our new import

def print_cluster_summary(clusters: dict):
    """Prints a user-friendly summary of the found clusters."""
    print("\n--- Cluster Partition Summary ---")
    
    # Group nodes by cluster_id
    grouped_clusters = {}
    for node, cluster_id in clusters.items():
        if cluster_id not in grouped_clusters:
            grouped_clusters[cluster_id] = []
        grouped_clusters[cluster_id].append(node)
    
    # Sort nodes within each cluster for consistent output
    for cid in grouped_clusters:
        grouped_clusters[cid].sort()
        
    for cid, members in sorted(grouped_clusters.items()):
        print(f"Cluster {cid}: {members}")
    print("---------------------------------")


def main():
    """
    Main entry point for the corruption network analysis pipeline.
    """
    # Argument parser remains the same
    parser = argparse.ArgumentParser(description="Solve the Correlation Clustering problem for multigraphs.")
    parser.add_argument('--data', type=str, required=True, help="Path to the input .csv data file.")
    parser.add_argument('--output_dir', type=str, required=True, help="Path to the directory where results will be saved.")
    parser.add_argument('--time_limit', type=int, default=3600, help="Time limit in seconds for the optimization solver. Default: 3600.")
    args = parser.parse_args()

    print("="*50)
    print("STARTING MULTIGRAPH CLUSTERING ANALYSIS")
    # ... (the rest of the header remains the same)
    print(f"Input instance: {args.data}")
    print("="*50)

    G = build_multigraph_from_csv(args.data)
    if not G:
        print("Failed to build the graph. Exiting.")
        return
    
    clusters, objective_value, execution_time = solve_multigraph_cc(G, time_limit=args.time_limit)
    if not clusters:
        print("Failed to solve the optimization model. Exiting.")
        return

    # --- NEW OUTPUT SECTION ---
    # 1. Print the user-friendly summary to the terminal
    print_cluster_summary(clusters)

    # 2. Save results to files
    print("\nSaving results...")
    try:
        os.makedirs(args.output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(args.data))[0]
        
        # 2a. Save the visualization
        viz_path = os.path.join(args.output_dir, f"{base_name}_visualization.png")
        visualize_and_save_graph(G, clusters, viz_path)
        
        # 2b. Save the clusters CSV
        clusters_csv_path = os.path.join(args.output_dir, f"{base_name}_clusters.csv")
        df_clusters = pd.DataFrame(list(clusters.items()), columns=['node', 'cluster_id'])
        df_clusters.sort_values(by=['cluster_id', 'node']).to_csv(clusters_csv_path, index=False)
        print(f"  - Cluster partition saved to: {clusters_csv_path}")
        
        # 2c. Save statistics
        stats_txt_path = os.path.join(args.output_dir, f"{base_name}_stats.txt")
        # ... (code to save stats.txt remains the same)
        with open(stats_txt_path, 'w') as f:
            f.write("--- Execution Statistics ---\n")
            f.write(f"Instance: {args.data}\n")
            f.write(f"Minimum Expected Imbalance: {objective_value}\n")
            # ... etc
        print(f"  - Execution stats saved to: {stats_txt_path}")

    except Exception as e:
        print(f"An error occurred while saving results: {e}")
            
    print("\n--- ANALYSIS COMPLETE ---")

if __name__ == '__main__':
    main()