# src/edu_management/genetic_algorithm.py

import random
import numpy as np
from typing import List, Dict, Tuple
from deap import base, creator, tools, algorithms

def evaluate_edu_fitness(
    chromosome: List[int], 
    disciplines: List[str], 
    slots: List[Dict], 
    students_enrolled: Dict[str, int], 
    food_cost: Dict[str, float], 
    calories: Dict[str, float],
    min_calories: float = 1200, 
    adherence_rate: float = 0.7
) -> Tuple[float, float]:
    """
    Calcula a aptidão do cromossomo (Grade de Horários).
    Retorna F1 (Cobertura Discente - a Maximizar) e F2 (Custo do RU - a Minimizar).
    """
    f1_cobertura = 0
    f2_custo = 0.0
    
    # Dicionário para contar a demanda de alunos em cada turno/dia
    alunos_por_turno = {} 
    
    # 1. Decodifica o Cromossomo (Alocações) e Calcula F1
    # O Cromossomo tem o tamanho do número de disciplinas.
    # O valor em chromosome[i] aponta para o ID do Slot (Dia, Turno, Sala).
    # Se chromosome[i] == -1, a aula não foi alocada.
    
    # Controle de Exclusividade (Checa se duas disciplinas caíram na mesma sala no mesmo horário)
    slots_usados = set()
    penalidade_exclusividade = 0
    
    for idx_disc, slot_id in enumerate(chromosome):
        if slot_id == -1:
            continue # Turma cancelada (sem cobertura)
            
        disc_name = disciplines[idx_disc]
        alunos = students_enrolled[disc_name]
        
        # Penaliza soluções inválidas (Duas turmas na mesma sala)
        if slot_id in slots_usados:
            penalidade_exclusividade += 10000
        slots_usados.add(slot_id)
        
        slot = slots[slot_id]
        f1_cobertura += alunos
        
        # Contabiliza o fluxo de alunos no RU
        chave_turno = (slot['Dia'], slot['Turno'])
        alunos_por_turno[chave_turno] = alunos_por_turno.get(chave_turno, 0) + alunos

    # 2. Calcula a Demanda do RU (F2) e Penalidades
    # O custo do RU é calculado base na comida mais barata para bater calorias,
    # somado aos "Pratos Feitos" obrigatórios pela taxa de adesão.
    
    dias = set([s['Dia'] for s in slots])
    turnos = set([s['Turno'] for s in slots])
    penalidade_min_aulas = 0
    
    for dia in dias:
        for turno in turnos:
            chave = (dia, turno)
            alunos_presentes = alunos_por_turno.get(chave, 0)
            
            # Penaliza se não tiver pelo menos 1 aula no turno! (A Restrição que fizemos no Gurobi)
            if alunos_presentes == 0:
                penalidade_min_aulas += 100
                
            # Demanda de pratos por taxa de adesão
            pratos_obrigatorios = int(alunos_presentes * adherence_rate)
            
            # Custo do Prato Principal
            custo_turno = pratos_obrigatorios * food_cost['prato_feito']
            calorias_turno = pratos_obrigatorios * calories['prato_feito']
            
            # Se faltar caloria para a cota mínima do restaurante, compra os complementos mais baratos
            calorias_faltantes = min_calories - calorias_turno
            if calorias_faltantes > 0:
                # Exemplo simplificado: Completa com a Salada Extra (que é barata)
                porcoes_salada = calorias_faltantes / calories['salada_extra']
                custo_turno += porcoes_salada * food_cost['salada_extra']
                
            f2_custo += custo_turno

    # Penalidades devem afetar SOMENTE a evolução, NÃO O CUSTO REAL F2!
    # Criamos um "Fitness Fake" para guiar o Genético, 
    # mas mantemos o custo financeiro exato para a Fronteira de Pareto.
    
    fitness_cobertura = f1_cobertura
    fitness_custo = f2_custo
    
    if penalidade_exclusividade > 0 or penalidade_min_aulas > 0:
        fitness_cobertura = max(0, f1_cobertura - 500) 
        fitness_custo += (penalidade_exclusividade + penalidade_min_aulas)

    # Só duas posições, para não bugar o DEAP Statistics
    return (-fitness_cobertura, fitness_custo)


def setup_edu_genetic_algorithm(
    disciplines: List[str], 
    rooms: List[str], 
    days: List[str], 
    shifts: List[str],
    students_enrolled: Dict[str, int],
    food_cost: Dict[str, float],
    calories: Dict[str, float],
    min_calories: float = 1200,
    adherence_rate: float = 0.7
):
    """
    Configura a Toolbox do DEAP para a Gestão Educacional.
    """
    # 1. Cria a lista 1D de todos os "Slots" possíveis (Dia x Turno x Sala)
    slots = []
    slot_id = 0
    for d in days:
        for t in shifts:
            for r in rooms:
                slots.append({'ID': slot_id, 'Dia': d, 'Turno': t, 'Sala': r})
                slot_id += 1
                
    num_slots = len(slots)
    num_disciplines = len(disciplines)

    # 2. Configura o DEAP para MINIMIZAR os dois retornos ( (-F1), F2 )
    if not hasattr(creator, "FitnessMin"):
        # Ignora os 2 últimos pesos! (0.0, 0.0)
        creator.create("FitnessMin", base.Fitness, weights=(-1.0, -1.0))
    if not hasattr(creator, "IndividualEdu"):
        creator.create("IndividualEdu", list, fitness=creator.FitnessMin)

    toolbox = base.Toolbox()

    # O cromossomo escolhe um Slot ID (0 a num_slots-1), ou -1 para "não alocar"
    toolbox.register("attr_slot", random.randint, -1, num_slots - 1)
    toolbox.register("individual", tools.initRepeat, creator.IndividualEdu, toolbox.attr_slot, n=num_disciplines)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Registra a função de Fitness
    toolbox.register("evaluate", evaluate_edu_fitness, 
                     disciplines=disciplines, slots=slots, 
                     students_enrolled=students_enrolled, 
                     food_cost=food_cost, calories=calories, 
                     min_calories=min_calories, adherence_rate=adherence_rate)

    toolbox.register("mate", tools.cxTwoPoint)
    toolbox.register("mutate", tools.mutUniformInt, low=-1, up=num_slots - 1, indpb=0.1)
    toolbox.register("select", tools.selNSGA2)

    return toolbox, slots