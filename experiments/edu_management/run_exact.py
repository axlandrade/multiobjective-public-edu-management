# experiments/edu_management/run_exact.py

import sys
import os
import pandas as pd
import time
from src.edu_management.optimization_model import solve_integrated_edu_management

def main():
    print("="*60)
    print("SIMULAÇÃO DE ESTRESSE: GESTÃO EDUCACIONAL (WSAC + WSMS)")
    print("="*60)

    # --- 1. Dados Fake: Uma Universidade Maior ---
    # 20 disciplinas diferentes disputando espaço
    disciplines = [f'Disc_{i:02d}' for i in range(1, 21)]
    
    # Apenas 5 salas (O Gurobi não vai conseguir espremer tudo num dia só!)
    rooms = ['Sala_101', 'Sala_102', 'Sala_103', 'Lab_01', 'Auditorio']
    
    days = ['Segunda', 'Terca', 'Quarta', 'Quinta', 'Sexta']
    shifts = ['Manha', 'Tarde', 'Noite']
    
    foods = ['prato_feito', 'salada_extra', 'suco', 'sobremesa']

    # --- 2. Parâmetros WSAC ---
    # Gerando número de alunos aleatórios, mas fixos para reprodutibilidade
    import random
    random.seed(42)
    students_enrolled = {d: random.randint(20, 90) for d in disciplines}
    
    # Capacidade das salas
    room_capacity = {
        'Sala_101': 40, 'Sala_102': 40, 'Sala_103': 50, 
        'Lab_01': 30, 'Auditorio': 100
    }

    # --- 3. Parâmetros WSMS ---
    food_cost = {'prato_feito': 8.50, 'salada_extra': 2.00, 'suco': 1.50, 'sobremesa': 3.00}
    calories = {'prato_feito': 800, 'salada_extra': 100, 'suco': 150, 'sobremesa': 250}

    print(f"Total de Disciplinas: {len(disciplines)}")
    print(f"Total de Salas: {len(rooms)}")
    print(f"Slots Disponíveis na Semana: {len(rooms) * len(days) * len(shifts)}")
    print(f"Total de Alunos Matriculados: {sum(students_enrolled.values())}\n")

    # --- 4. O Teste de Estresse ---
    print("--- Teste de Estresse: Foco Total no Ensino (lambda = 1.0) ---")
    print("Iniciando otimização no Gurobi... (Isso pode demorar alguns segundos!)")
    
    start_time = time.time()
    
    res1 = solve_integrated_edu_management(
        disciplines=disciplines, rooms=rooms, days=days, shifts=shifts, foods=foods,
        students_enrolled=students_enrolled, room_capacity=room_capacity,
        food_cost=food_cost, calories=calories, min_calories=1200,
        adherence_rate=0.7, lambda_weight=1.0, time_limit=120 # Demos 2 minutos para ele pensar
    )
    
    exec_time = time.time() - start_time
    
    if not res1:
        print("\nO Gurobi não conseguiu encontrar uma solução no tempo limite!")
        return

    print(f"\n[SUCESSO] Otimização concluída em {exec_time:.2f} segundos!")
    print(f"Alunos Cobertos: {res1['f1_alunos_cobertos']} de {sum(students_enrolled.values())}")
    print(f"Custo do RU: R$ {res1['f2_custo_total']}\n")

    print("[Resumo da Grade de Aulas (Dias Utilizados)]:")
    
    # Contar quantas aulas foram alocadas em cada dia
    aulas_por_dia = {d: 0 for d in days}
    for aula in res1['grade_horaria']:
        aulas_por_dia[aula['Dia']] += 1
        
    for dia, qtd in aulas_por_dia.items():
        print(f"  {dia}: {qtd} aulas alocadas.")

    print("\n[Resumo da Demanda do RU (Pratos Feitos)]:")
    for item in res1['cardapio_ru']:
        if item['Item'] == 'prato_feito':
            print(f"  {item['Dia']} ({item['Turno']}): Servir {item['Quantidade']} pratos.")

if __name__ == "__main__":
    main()