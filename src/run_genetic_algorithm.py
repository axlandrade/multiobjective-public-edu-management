# src/run_genetic_algorithm.py

import random
import argparse
import numpy as np
import networkx as nx
import os
import pandas as pd

from deap import base, creator, tools, algorithms

# Import our custom modules
from graph_constructor import build_multigraph_from_csv
from genetic_algorithm import setup_genetic_algorithm


def main():
    """
    [English]
    Main script to run the NSGA-II genetic algorithm for the multi-objective
    correlation clustering problem on multigraphs.

    [Português]
    Script principal para executar o algoritmo genético NSGA-II para o problema
    de correlation clustering multiobjetivo em multigrafos.
    """
    parser = argparse.ArgumentParser(
        description="Run the NSGA-II Genetic Algorithm.")
    parser.add_argument('--data', required=True,
                        help="Path to the input .csv data file.")
    args = parser.parse_args()

    # --- 1. Load Data and Setup ---
    print(f"--- Loading data from: {args.data} ---")
    G = build_multigraph_from_csv(args.data)
    if not G:
        return

    nodes = sorted(list(G.nodes()))
    toolbox = setup_genetic_algorithm(nodes, G)

    # --- 2. Genetic Algorithm Parameters ---
    POP_SIZE = 200
    CXPB = 0.7
    MUTPB = 0.2
    NGEN = 100

    print("\n--- Genetic Algorithm Parameters ---")
    print(f"Population Size: {POP_SIZE}")
    print(f"Crossover Probability: {CXPB}")
    print(f"Mutation Probability: {MUTPB}")
    print(f"Number of Generations: {NGEN}")

    # --- 3. Run the NSGA-II Algorithm ---
    print("\n--- Starting Evolution (NSGA-II) ---")

    pop = toolbox.population(n=POP_SIZE)
    hof = tools.ParetoFront()
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean, axis=0)
    stats.register("min", np.min, axis=0)
    stats.register("max", np.max, axis=0)

    algorithms.eaMuPlusLambda(
        population=pop,
        toolbox=toolbox,
        mu=POP_SIZE,
        lambda_=POP_SIZE,
        cxpb=CXPB,
        mutpb=MUTPB,
        ngen=NGEN,
        stats=stats,
        halloffame=hof,
        verbose=True
    )

    print("--- Evolution Finished ---")

    # --- CORREÇÃO: Este bloco deve estar DENTRO da função main() ---
    # --- 4. Save and Print the Final Pareto Front ---
    print(f"\n--- Found {len(hof)} Non-Dominated Solutions (Pareto Front) ---")

    pareto_data = []
    for ind in hof:
        # Note: A ordem dos valores de fitness é a mesma retornada pela sua função
        # evaluate_fitness: (desequilíbrio, num_clusters)
        f1_disagreement, f2_clusters = ind.fitness.values
        pareto_data.append({
            'num_clusters_f2': int(f2_clusters),
            'disagreement_f1': f1_disagreement
        })

    df_pareto = pd.DataFrame(pareto_data)
    df_pareto = df_pareto.sort_values(by=['num_clusters_f2']).drop_duplicates()

    output_dir = "results_ga"
    os.makedirs(output_dir, exist_ok=True)
    instance_name = os.path.splitext(os.path.basename(args.data))[0]
    pareto_csv_path = os.path.join(output_dir, f"pareto_{instance_name}.csv")
    df_pareto.to_csv(pareto_csv_path, index=False)
    print(f"  - Pareto front saved to: {pareto_csv_path}")

    print("\nNum_Clusters (f2) | Disagreement (f1)")
    print("---------------------------------------")
    for index, row in df_pareto.iterrows():
        print(f"{row['num_clusters_f2']:>16} | {row['disagreement_f1']:<18.4f}")


if __name__ == '__main__':
    main()
