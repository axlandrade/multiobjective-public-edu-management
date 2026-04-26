# src/public_management/visualizer.py

import networkx as nx
import matplotlib.pyplot as plt
import random

def visualize_and_save_graph(G: nx.MultiGraph, clusters: dict, output_path: str):
    """
    Generates and saves a visualization of the clustered multigraph.

    Args:
        G: The original MultiGraph object.
        clusters: A dictionary mapping each node to its cluster ID.
        output_path: The path to save the output image file (e.g., '.../result.png').
    """
    print("  - Generating graph visualization...")
    
    # 1. Define positions for the nodes for a clear layout
    pos = nx.spring_layout(G, seed=42, k=0.9)

    # 2. Create a color map for the clusters
    unique_cluster_ids = sorted(list(set(clusters.values())))
    colors = [plt.cm.get_cmap('viridis', len(unique_cluster_ids))(i) for i in range(len(unique_cluster_ids))]
    color_map = {cid: color for cid, color in zip(unique_cluster_ids, colors)}
    node_colors = [color_map[clusters[node]] for node in G.nodes()]

    plt.figure(figsize=(12, 8))

    # 3. Draw the nodes, colored by their cluster
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2000, alpha=0.9)

    # 4. Draw the edges, colored by their nature (positive/negative)
    edge_colors = []
    for u, v, data in G.edges(data=True):
        color = 'g' if data['positive_prob'] > 0.5 else 'r'
        edge_colors.append(color)
        
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, alpha=0.6, width=1.5)

    # 5. Draw the node labels
    nx.draw_networkx_labels(G, pos, font_size=12, font_color='white', font_weight='bold')

    plt.title("Graph Partition into Clusters", size=18)
    plt.axis('off')
    
    # 6. Save the figure
    try:
        plt.savefig(output_path, bbox_inches='tight', dpi=300)
        print(f"  - Visualization saved to: {output_path}")
    except Exception as e:
        print(f"  - Error saving visualization: {e}")
    
    plt.close()