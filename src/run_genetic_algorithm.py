# src/run_genetic_algorithm.py

import random
import argparse
import numpy as np
import networkx as nx

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
    parser = argparse.ArgumentParser(description="Run the NSGA-II Genetic Algorithm.")
    parser.add_argument('--data', required=True, help="Path to the input .csv data file.")
    args = parser.parse_args()

    # --- 1. Load Data and Setup ---
    print(f"--- Loading data from: {args.data} ---")
    G = build_multigraph_from_csv(args.data)
    if not G:
        return

    nodes = sorted(list(G.nodes()))
    toolbox = setup_genetic_algorithm(nodes, G)

    # --- 2. Genetic Algorithm Parameters ---
    # [English] You can tune these parameters to improve results.
    # [Português] Você pode ajustar estes parâmetros para melhorar os resultados.
    POP_SIZE = 100        # Population size / Tamanho da população
    CXPB = 0.7            # Crossover probability / Probabilidade de cruzamento
    MUTPB = 0.2           # Mutation probability / Probabilidade de mutação
    NGEN = 50             # Number of generations / Número de gerações

    print("\n--- Genetic Algorithm Parameters ---")
    print(f"Population Size: {POP_SIZE}")
    print(f"Crossover Probability: {CXPB}")
    print(f"Mutation Probability: {MUTPB}")
    print(f"Number of Generations: {NGEN}")

    # --- 3. Run the NSGA-II Algorithm ---
    print("\n--- Starting Evolution (NSGA-II) ---")
    
    # [English] Initialize the population.
    # [Português] Inicializa a população.
    pop = toolbox.population(n=POP_SIZE)
    
    # [English] This object will store the best non-dominated individuals found.
    # [Português] Este objeto irá guardar os melhores indivíduos não-dominados encontrados.
    hof = tools.ParetoFront()

    # [English] This will store statistics if you want to track progress.
    # [Português] Isto guardará estatísticas se você quiser acompanhar o progresso.
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean, axis=0)
    stats.register("min", np.min, axis=0)
    stats.register("max", np.max, axis=0)

    # [English] This is the main evolutionary loop from the DEAP library.
    # [Português] Este é o loop evolucionário principal da biblioteca DEAP.
    algorithms.eaMuPlusLambda(
        population=pop,
        toolbox=toolbox,
        mu=POP_SIZE,       # Number of individuals to select for the next generation
        lambda_=POP_SIZE,  # Number of children to produce at each generation
        cxpb=CXPB,
        mutpb=MUTPB,
        ngen=NGEN,
        stats=stats,
        halloffame=hof,
        verbose=True
    )

    print("--- Evolution Finished ---")

    # --- 4. Print the Final Pareto Front ---
    print(f"\n--- Found {len(hof)} Non-Dominated Solutions (Pareto Front) ---")
    print("Num_Clusters (f2) | Disagreement (f1)")
    print("---------------------------------------")
    
    # Sort solutions for clearer presentation
    sorted_solutions = sorted(list(hof), key=lambda ind: ind.fitness.values[1])

    for ind in sorted_solutions:
        f2_clusters, f1_disagreement = ind.fitness.values
        print(f"{int(f2_clusters):>16} | {f1_disagreement:<18.4f}")

if __name__ == '__main__':
    main()