# experiments/edu_management/run_heuristic.py

import sys
import os
import time
import json
import pandas as pd
import numpy as np
import multiprocessing

from deap import tools, algorithms
from src.edu_management.genetic_algorithm import setup_edu_genetic_algorithm

def main():
    print("="*60)
    print("GERAÇÃO DA FRONTEIRA DE PARETO EDUCACIONAL VIA NSGA-II")
    print("="*60)

    # --- 1. Dados do Teste de Estresse ---
    disciplines = [f'Disc_{i:02d}' for i in range(1, 21)]
    rooms = ['Sala_101', 'Sala_102', 'Sala_103', 'Lab_01', 'Auditorio']
    days = ['Segunda', 'Terca', 'Quarta', 'Quinta', 'Sexta']
    shifts = ['Manha', 'Tarde', 'Noite']
    foods = ['prato_feito', 'salada_extra', 'suco', 'sobremesa']

    import random
    random.seed(42)
    students_enrolled = {d: random.randint(20, 90) for d in disciplines}
    
    food_cost = {'prato_feito': 8.50, 'salada_extra': 2.00, 'suco': 1.50, 'sobremesa': 3.00}
    calories = {'prato_feito': 800, 'salada_extra': 100, 'suco': 150, 'sobremesa': 250}

    print(f"Total de Disciplinas: {len(disciplines)}")
    print(f"Slots Disponíveis na Semana: {len(rooms) * len(days) * len(shifts)}")
    print(f"Total de Alunos Matriculados: {sum(students_enrolled.values())}\n")

    # --- 2. Parâmetros do Algoritmo Genético ---
    POP_SIZE = 300
    NGEN = 400      # 200 gerações de cruzamento
    CXPB = 0.5      # 50% de chance de cruzar o DNA (trocar horários entre soluções boas)
    MUTPB = 0.3     # 30% de chance de mutação (trocar uma aula de sala/turno do nada)

    toolbox, slots = setup_edu_genetic_algorithm(
        disciplines=disciplines, rooms=rooms, days=days, shifts=shifts,
        students_enrolled=students_enrolled, food_cost=food_cost, calories=calories,
        min_calories=1200, adherence_rate=0.7
    )

    # Processamento paralelo (usa os múltiplos núcleos do seu CPU)
    pool = multiprocessing.Pool()
    toolbox.register("map", pool.map)

    # --- 3. Evolução (NSGA-II) ---
    print(f"--- Iniciando Evolução (Pop: {POP_SIZE}, Gerações: {NGEN}) ---")
    start_time = time.time()
    
    pop = toolbox.population(n=POP_SIZE)
    hof = tools.ParetoFront() # Guarda as melhores soluções não-dominadas
    
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean, axis=0)
    stats.register("min", np.min, axis=0)
    stats.register("max", np.max, axis=0)

    # Roda a mágica da evolução DEAP
    algorithms.eaMuPlusLambda(
        population=pop, toolbox=toolbox, mu=POP_SIZE, lambda_=POP_SIZE,
        cxpb=CXPB, mutpb=MUTPB, ngen=NGEN, stats=stats, halloffame=hof, verbose=True
    )

    pool.close()
    total_time = time.time() - start_time
    
    print(f"\n--- Evolução Finalizada em {total_time:.2f} segundos ---")
    print(f"Soluções de Pareto Encontradas: {len(hof)}")

    # --- 4. Extração e Salvamento da Fronteira ---
    pareto_data = []
    
        # Precisamos importar a função de avaliação original aqui
    from src.edu_management.genetic_algorithm import evaluate_edu_fitness
    
    pareto_data = []
    
    for idx, ind in enumerate(hof):
        # A fitness do DEAP ainda carrega a multa fantasma.
        f1_neg, f2_custo_mutante = ind.fitness.values
        
        # Vamos rodar o cromossomo de novo na nossa "calculadora", 
        # mas ignorando as multas que o Gurobi pedia e olhando apenas
        # pros números crus da faculdade.
        # Mas podemos descobrir isso facilmente reavaliando o cromossomo cru!
        
        # Simula o fluxo:
        f1_alunos_reais = 0
        alunos_por_turno = {} 
        slots_usados = set()
        invalido = False
        
        for idx_disc, slot_id in enumerate(ind):
            if slot_id == -1: continue
            
            if slot_id in slots_usados:
                invalido = True
                break
            slots_usados.add(slot_id)
            
            disc_name = disciplines[idx_disc]
            alunos = students_enrolled[disc_name]
            f1_alunos_reais += alunos
            
            slot = slots[slot_id]
            chave_turno = (slot['Dia'], slot['Turno'])
            alunos_por_turno[chave_turno] = alunos_por_turno.get(chave_turno, 0) + alunos

        # Se o cromossomo no Hall of Fame tiver 2 turmas na mesma sala, ignoramos
        if invalido: 
            continue
            
        f2_custo_real = 0.0
        for dia in set([s['Dia'] for s in slots]):
            for turno in set([s['Turno'] for s in slots]):
                chave = (dia, turno)
                alunos_presentes = alunos_por_turno.get(chave, 0)
                
                pratos = int(alunos_presentes * 0.7)
                custo_turno = pratos * food_cost['prato_feito']
                calorias_turno = pratos * calories['prato_feito']
                
                calorias_faltantes = 1200 - calorias_turno
                if calorias_faltantes > 0:
                    porcoes_salada = calorias_faltantes / calories['salada_extra']
                    custo_turno += porcoes_salada * food_cost['salada_extra']
                    
                f2_custo_real += custo_turno

        # Filtra opções muito acima do budget
        if f2_custo_real > 8000 or f1_alunos_reais == 0:
            continue
            
        pareto_data.append({
            'sol_id': f"NSGA_{idx:03d}",
            'f1_alunos': int(f1_alunos_reais),
            'f2_custo_ru': round(f2_custo_real, 2),
            'cromossomo': str(list(ind))
        })

    df_pareto = pd.DataFrame(pareto_data).sort_values(by=['f1_alunos', 'f2_custo_ru']).drop_duplicates()
    
    print("\n--- FRONTEIRA DE PARETO (NSGA-II) ---")
    print(df_pareto[['sol_id', 'f1_alunos', 'f2_custo_ru']].to_string(index=False))

    os.makedirs('results_edu', exist_ok=True)
    df_pareto.to_csv('results_edu/pareto_nsga2_wsac_wsms.csv', index=False)
    print("\nFronteira inteira e grades codificadas salvas em 'results_edu/pareto_nsga2_wsac_wsms.csv'!")

if __name__ == "__main__":
    main()