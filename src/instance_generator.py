# src/instance_generator.py

import pandas as pd
import numpy as np
import os

def generate_multigraph_instances():
    """
    Generates multigraph CSV instances based on Ponciano's (2017) run1 graph
    and the probability tables (Table 8, p. 39).
    """
    # Base structure of the run1 graph (14 edges)
    # Based on Figure 14, p. 43 of Ponciano (2017)
    run1_edges = [
        ('I1', 'S11'), ('I1', 'S12'), ('I1', 'S31'), ('I1', 'S32'), ('I1', 'S33'),
        ('I2', 'S11'), ('I2', 'S12'), ('I2', 'S21'), ('I2', 'S22'),
        ('I3', 'S12'), ('I3', 'S21'), ('I3', 'S22'), ('I3', 'S31'), ('I3', 'S33')
    ]

    # Probabilities from Table 8, p. 39 of Ponciano (2017)
    prob_sets = {
        'P1': [0.6, 0.8, 0.7, 0.8, 0.9, 0.8, 0.7, 0.7, 1.0, 0.6, 0.6, 0.8, 0.7, 0.7],
        'P2': [0.9, 0.6, 0.5, 0.7, 0.6, 0.8, 0.8, 0.7, 0.5, 0.7, 0.6, 0.9, 0.6, 0.7],
        'P3': [0.5, 0.7, 0.7, 0.7, 0.7, 0.7, 0.9, 0.9, 0.6, 0.9, 0.9, 0.7, 0.9, 0.7],
        'P4': [0.9, 0.9, 0.9, 0.5, 0.6, 0.5, 0.8, 0.6, 0.7, 0.8, 0.8, 0.9, 0.9, 0.6],
        'P5': [1.0, 0.6, 0.8, 0.5, 0.9, 0.9, 1.0, 0.8, 1.0, 0.8, 0.9, 0.8, 0.8, 0.9],
        'P6': [0.6, 0.7, 0.8, 0.7, 1.0, 0.8, 0.9, 0.6, 0.8, 0.9, 0.8, 0.7, 0.9, 0.9],
        'P7': [0.9, 0.6, 0.7, 0.6, 0.7, 1.0, 0.9, 1.0, 1.0, 0.6, 0.7, 0.7, 0.5, 0.6],
        'P8': [0.7, 0.8, 0.5, 0.6, 0.8, 0.8, 0.8, 0.9, 0.7, 0.8, 0.9, 0.7, 0.6, 1.0],
        'P9': [1.0, 0.6, 0.7, 1.0, 0.7, 0.6, 0.8, 0.8, 0.6, 0.7, 0.9, 0.5, 0.6, 0.8],
        'P10': [0.9, 1.0, 0.6, 0.7, 0.7, 0.9, 0.6, 0.6, 0.9, 0.8, 0.7, 0.6, 0.8, 0.7]
    } # 
    
    # --- Parameters for Multigraph Expansion ---
    K = 5  # Number of parallel edges (contracts) to generate for each original edge
    STD_DEV = 0.05 # Standard deviation for probability variation
    
    output_dir = 'data'
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Generating multigraph instances (K={K}) in folder '{output_dir}'...")

    # Iterate through each probability set (P1, P2, ...)
    for set_name, probabilities in prob_sets.items():
        multigraph_data = []
        
        # Iterate through each of the 14 original edges and its base probability
        for i, base_edge in enumerate(run1_edges):
            base_prob = probabilities[i]
            
            # Generate K new edges with varied probabilities
            new_probs = np.random.normal(loc=base_prob, scale=STD_DEV, size=K)
            # Clip values to ensure they are valid probabilities [0, 1]
            new_probs = np.clip(new_probs, 0.0, 1.0)
            
            for prob in new_probs:
                multigraph_data.append({
                    'node_1': base_edge[0],
                    'node_2': base_edge[1],
                    'positive_prob': round(prob, 4), # Arredonda para 4 casas decimais
                    'weight': 1.0
                })
        
        # Create a DataFrame and save to CSV
        df = pd.DataFrame(multigraph_data)
        file_name = f'run1_{set_name}_k{K}.csv'
        output_path = os.path.join(output_dir, file_name)
        df.to_csv(output_path, index=False)
        print(f"  - Successfully created '{output_path}' with {len(df)} edges.")

if __name__ == '__main__':
    generate_multigraph_instances()