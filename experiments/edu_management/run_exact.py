# experiments/edu_management/run_exact.py

import sys
import os
import pandas as pd
import time
from src.edu_management.optimization_model import solve_integrated_edu_management

def main():
    print("="*60)
    print("VARREDURA DE PARETO (SOMA PONDERADA): GESTÃO EDUCACIONAL (WSAC + WSMS)")
    print("="*60)

    # --- 1. Dados Fake: Uma Universidade Maior ---
    disciplines = [f'Disc_{i:02d}' for i in range(1, 21)]
    rooms = ['Sala_101', 'Sala_102', 'Sala_103', 'Lab_01', 'Auditorio']
    days = ['Segunda', 'Terca', 'Quarta', 'Quinta', 'Sexta']
    shifts = ['Manha', 'Tarde', 'Noite']
    foods = ['prato_feito', 'salada_extra', 'suco', 'sobremesa']

    import random
    random.seed(42)
    students_enrolled = {d: random.randint(20, 90) for d in disciplines}
    
    room_capacity = {
        'Sala_101': 40, 'Sala_102': 40, 'Sala_103': 50, 
        'Lab_01': 30, 'Auditorio': 100
    }

    food_cost = {'prato_feito': 8.50, 'salada_extra': 2.00, 'suco': 1.50, 'sobremesa': 3.00}
    calories = {'prato_feito': 800, 'salada_extra': 100, 'suco': 150, 'sobremesa': 250}

    print(f"Total de Disciplinas: {len(disciplines)}")
    print(f"Total de Salas: {len(rooms)}")
    print(f"Total de Alunos Matriculados: {sum(students_enrolled.values())}\n")

    # --- 2. Configurando a Varredura de Lambda ---
    # Fazendo um pente fino de 0.0 até 1.0 (com saltos de 0.05)
    # e incluindo pontos sensíveis na quebra perto do 1.0
    lambdas_to_test = [
        0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 
        0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 
        0.90, 0.95, 0.98, 0.999, 1.0
    ]
    
    resultados_exatos = []
    
    # Criar pasta para salvar resultados
    os.makedirs('results_edu', exist_ok=True)

    print("--- Iniciando Otimização Sequencial no Gurobi ---")
    start_total_time = time.time()

    for l_weight in lambdas_to_test:
        print(f"\n>> Rodando cenário com Lambda = {l_weight} ...")
        
        start_run = time.time()
        
        # Chamada do modelo exato (PLI)
        res = solve_integrated_edu_management(
            disciplines=disciplines, rooms=rooms, days=days, shifts=shifts, foods=foods,
            students_enrolled=students_enrolled, room_capacity=room_capacity,
            food_cost=food_cost, calories=calories, min_calories=1200,
            adherence_rate=0.7, lambda_weight=l_weight, time_limit=120 
        )
        
        exec_time = time.time() - start_run
        
        if res:
            f1 = int(res['f1_alunos_cobertos'])
            f2 = round(res['f2_custo_total'], 2)
            print(f"[OK] {exec_time:.2f}s | Alunos: {f1} | Custo RU: R$ {f2}")
            
            resultados_exatos.append({
                'lambda': l_weight,
                'f1_alunos': f1,
                'f2_custo_ru': f2,
                'tempo_execucao_s': round(exec_time, 2)
            })
        else:
            print(f"[FALHA] Gurobi não convergiu para Lambda={l_weight} no tempo limite.")

    total_time = time.time() - start_total_time

    # --- 3. Apresentação e Exportação ---
    print("\n" + "="*60)
    print(f"RESUMO DA FRONTEIRA EXATA (Tempo Total: {total_time:.2f}s)")
    print("="*60)
    
    df_exato = pd.DataFrame(resultados_exatos)
    
    # Exibir a tabela bonita no terminal
    print(df_exato.to_string(index=False))
    
    # Salvar em CSV para comparar com o Genético depois
    csv_path = 'results_edu/pareto_gurobi_exact.csv'
    df_exato.to_csv(csv_path, index=False)
    print(f"\n[!] Tabela exata salva em: {csv_path}")

if __name__ == "__main__":
    main()