# src/run_ga_real_data.py

import random
import argparse
import numpy as np
import networkx as nx
import os
import pandas as pd
import time
import multiprocessing
import json

from deap import base, creator, tools, algorithms

# Import our custom modules
from graph_constructor import build_multigraph_from_csv
from genetic_algorithm import setup_genetic_algorithm


def main():
    """
    [English]
    Main script to run the NSGA-II genetic algorithm on REAL-WORLD data for the 
    multi-objective correlation clustering problem.

    [Português]
    Script principal para executar o algoritmo genético NSGA-II em DADOS REAIS para o problema
    de correlation clustering multiobjetivo.
    """
    parser = argparse.ArgumentParser(
        description="Run the NSGA-II Genetic Algorithm on Real-World Data.")
    parser.add_argument('--data', required=True,
                        help="Path to the real-world network .csv file.")
    parser.add_argument('--output_dir', default='results_real_data',
                        help="Directory to save the results.")

    parser.add_argument('--pop_size', type=int, default=300,
                        help="Population size for the GA.")
    parser.add_argument('--ngen', type=int, default=200,
                        help="Number of generations for the GA.")
    parser.add_argument('--cxpb', type=float, default=0.5,
                        help="Crossover probability.")
    parser.add_argument('--mutpb', type=float, default=0.5,
                        help="Mutation probability.")

    args = parser.parse_args()

    start_time = time.time()
    print("="*60)
    print("STARTING PARALLEL GENETIC ALGORITHM ANALYSIS ON REAL-WORLD DATA")
    print("="*60)

    # --- 1. Load Data and Setup ---
    print(f"--- Loading data from: {args.data} ---")
    G = build_multigraph_from_csv(args.data)
    if not G:
        return

    nodes = sorted(list(G.nodes()))
    toolbox = setup_genetic_algorithm(nodes, G)

    pool = multiprocessing.Pool()
    toolbox.register("map", pool.map)

    print("\n--- Genetic Algorithm Parameters ---")
    print(f"Population Size: {args.pop_size}")
    print(f"Number of Generations: {args.ngen}")
    print(f"Crossover Probability: {args.cxpb}")
    print(f"Mutation Probability: {args.mutpb}")

    # --- 3. Run the NSGA-II Algorithm ---
    print("\n--- Starting Evolution (NSGA-II) in Parallel ---")

    pop = toolbox.population(n=args.pop_size)
    hof = tools.ParetoFront()
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean, axis=0)
    stats.register("min", np.min, axis=0)
    stats.register("max", np.max, axis=0)

    algorithms.eaMuPlusLambda(
        population=pop,
        toolbox=toolbox,
        mu=args.pop_size,
        lambda_=args.pop_size,
        cxpb=args.cxpb,
        mutpb=args.mutpb,
        ngen=args.ngen,
        stats=stats,
        halloffame=hof,
        verbose=True
    )

    pool.close()
    print("--- Evolution Finished ---")

    # --- 4. Save and Print the Final Pareto Front (Scores and Partitions) ---
    total_time_minutes = (time.time() - start_time) / 60
    print(
        f"\n--- Found {len(hof)} Non-Dominated Solutions (Total Time: {total_time_minutes:.2f} minutes) ---")

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    instance_name = os.path.splitext(os.path.basename(args.data))[0]

    pareto_data = []
    solution_partitions = {}
    solution_counter = 0

    for ind in hof:
        f1_disagreement, f2_clusters = ind.fitness.values
        solution_id = f"solution_{solution_counter}"

        pareto_data.append({
            'solution_id': solution_id,
            'num_clusters_f2': int(f2_clusters),
            'disagreement_f1': f1_disagreement
        })
        solution_partitions[solution_id] = list(ind)
        solution_counter += 1

    # Save the scores to a CSV file
    df_pareto = pd.DataFrame(pareto_data).sort_values(
        by=['num_clusters_f2']).drop_duplicates()
    pareto_csv_path = os.path.join(
        args.output_dir, f"pareto_{instance_name}.csv")
    df_pareto.to_csv(pareto_csv_path, index=False)
    print(f"  - Pareto front scores saved to: {pareto_csv_path}")

    # Save the full partitions to a JSON file for qualitative analysis
    partitions_path = os.path.join(
        args.output_dir, f"partitions_{instance_name}.json")
    with open(partitions_path, 'w') as f:
        json.dump(solution_partitions, f, indent=4)
    print(f"  - Solution partitions saved to: {partitions_path}")

    # --- NOVO BLOCO PARA SALVAR ESTATÍSTICAS ---
    # [English] Save execution summary (parameters and time) to a JSON file.
    # [Português] Salva o sumário da execução (parâmetros e tempo) em um arquivo JSON.
    stats_data = {
        'instance_file': args.data,
        'population_size': args.pop_size,
        'generations': args.ngen,
        'crossover_probability': args.cxpb,
        'mutation_probability': args.mutpb,
        'total_execution_time_minutes': round(total_time_minutes, 2),
        'num_pareto_solutions': len(hof)
    }
    stats_path = os.path.join(
        args.output_dir, f"stats_{instance_name}.json")
    with open(stats_path, 'w') as f:
        json.dump(stats_data, f, indent=4)
    print(f"  - Execution stats saved to: {stats_path}")
    # --- FIM DO NOVO BLOCO ---

    # Print a summary to the console
    print("\nSolution ID      | Num_Clusters (f2) | Disagreement (f1)")
    print("-------------------------------------------------------------")
    for index, row in df_pareto.iterrows():
        print(
            f"{row['solution_id']:<16} | {row['num_clusters_f2']:>17} | {row['disagreement_f1']:<18.4f}")


if __name__ == '__main__':
    main()
