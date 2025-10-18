# experiments/heuristic/run_genetic_algorithm.py

from src.genetic_algorithm import setup_genetic_algorithm
from src.graph_constructor import build_multigraph_from_csv
from deap import algorithms, base, creator, tools
import numpy as np
import pandas as pd
import time
import multiprocessing
import json
import argparse
import sys
import os

# Adiciona a pasta raiz do projeto ao caminho de busca do Python
project_root = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def run_ga_experiment(data_path, output_dir, pop_size, ngen, cxpb, mutpb):
    """
    Função principal que executa a lógica do Algoritmo Genético.
    Recebe os parâmetros e retorna os resultados.
    """
    start_time = time.time()

    # --- Carregar Dados e Configurar ---
    print(f"--- Loading data from: {data_path} ---")
    G = build_multigraph_from_csv(data_path)
    if not G:
        return None, None, None

    nodes = sorted(list(G.nodes()))
    toolbox = setup_genetic_algorithm(nodes, G)

    pool = multiprocessing.Pool()
    toolbox.register("map", pool.map)

    print("\n--- Genetic Algorithm Parameters ---")
    print(
        f"Population Size: {pop_size}, Generations: {ngen}, CXPB: {cxpb}, MUTPB: {mutpb}")

    # --- Executar Algoritmo ---
    print("\n--- Starting Evolution (NSGA-II) ---")
    pop = toolbox.population(n=pop_size)
    hof = tools.ParetoFront()
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean, axis=0)
    stats.register("min", np.min, axis=0)
    stats.register("max", np.max, axis=0)

    algorithms.eaMuPlusLambda(
        population=pop, toolbox=toolbox, mu=pop_size, lambda_=pop_size,
        cxpb=cxpb, mutpb=mutpb, ngen=ngen, stats=stats, halloffame=hof, verbose=True
    )
    pool.close()
    print("--- Evolution Finished ---")

    # --- Processar e Salvar Resultados ---
    total_time_minutes = (time.time() - start_time) / 60
    os.makedirs(output_dir, exist_ok=True)
    instance_name = os.path.splitext(os.path.basename(data_path))[0]

    pareto_data, solution_partitions = [], {}
    int_to_node = {i: name for i, name in enumerate(nodes)}
    for i, ind in enumerate(hof):
        f1, f2 = ind.fitness.values
        sol_id = f"solution_{i}"
        pareto_data.append(
            {'solution_id': sol_id, 'num_clusters_f2': int(f2), 'disagreement_f1': f1})
        solution_partitions[sol_id] = {
            int_to_node[n]: int_to_node[ind[n]] for n in range(len(ind))}

    df_pareto = pd.DataFrame(pareto_data).sort_values(
        by=['num_clusters_f2']).drop_duplicates()

    stats_data = {
        'instance_file': data_path, 'population_size': pop_size, 'generations': ngen,
        'crossover_probability': cxpb, 'mutation_probability': mutpb,
        'total_execution_time_minutes': round(total_time_minutes, 2),
        'num_pareto_solutions': len(df_pareto)
    }

    # Salvar arquivos (opcional, pois a UI mostrará os resultados)
    # ...

    return stats_data, df_pareto, solution_partitions


def main():
    """
    Função que lida com a execução via linha de comando.
    """
    parser = argparse.ArgumentParser(
        description="Run the NSGA-II Genetic Algorithm.")
    parser.add_argument('--data', required=True,
                        help="Path to the input .csv data file.")
    # Adicione outros argumentos se necessário (pop_size, ngen, etc.)
    args = parser.parse_args()

    # Parâmetros padrão para execução via terminal
    run_ga_experiment(
        data_path=args.data, output_dir="results_terminal",
        pop_size=200, ngen=100, cxpb=0.7, mutpb=0.2
    )


if __name__ == '__main__':
    main()
