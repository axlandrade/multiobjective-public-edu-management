# src/run_ga_real_data.py

import random
import argparse
import numpy as np
import networkx as nx
import os
import pandas as pd
import time
import multiprocessing  # --- ALTERAÇÃO 1: Importar a biblioteca ---

from deap import base, creator, tools, algorithms

# Import our custom modules
from graph_constructor import build_multigraph_from_csv
from genetic_algorithm import setup_genetic_algorithm

# A função main() continua exatamente a mesma...


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
    parser.add_argument('--cxpb', type=float, default=0.8,
                        help="Crossover probability.")
    parser.add_argument('--mutpb', type=float, default=0.2,
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

    # --- ALTERAÇÃO 2: Configurar o Pool de Processamento Paralelo ---
    # [English] Setup a multiprocessing pool.
    # [Português] Configura um pool de processos para execução paralela.
    pool = multiprocessing.Pool()
    toolbox.register("map", pool.map)
    # ----------------------------------------------------------------

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

    # --- ALTERAÇÃO 3: Fechar o Pool ao final ---
    pool.close()
    # ---------------------------------------------

    print("--- Evolution Finished ---")

    # --- 4. Save and Print the Final Pareto Front ---
    # (O restante do código para salvar e imprimir continua igual)
    total_time_minutes = (time.time() - start_time) / 60
    print(
        f"\n--- Found {len(hof)} Non-Dominated Solutions (Total Time: {total_time_minutes:.2f} minutes) ---")

    pareto_data = []
    for ind in hof:
        f1_disagreement, f2_clusters = ind.fitness.values
        pareto_data.append({
            'num_clusters_f2': int(f2_clusters),
            'disagreement_f1': f1_disagreement
        })

    df_pareto = pd.DataFrame(pareto_data)
    df_pareto = df_pareto.sort_values(by=['num_clusters_f2']).drop_duplicates()

    os.makedirs(args.output_dir, exist_ok=True)
    instance_name = os.path.splitext(os.path.basename(args.data))[0]
    pareto_csv_path = os.path.join(
        args.output_dir, f"pareto_{instance_name}.csv")
    df_pareto.to_csv(pareto_csv_path, index=False)
    print(f"  - Pareto front saved to: {pareto_csv_path}")

    print("\nNum_Clusters (f2) | Disagreement (f1)")
    print("---------------------------------------")
    for index, row in df_pareto.iterrows():
        print(f"{row['num_clusters_f2']:>16} | {row['disagreement_f1']:<18.4f}")


if __name__ == '__main__':
    main()
