# src/edu_management/optimization_model.py

from ortools.linear_solver import pywraplp

def solve_integrated_edu_management(
    disciplines, rooms, days, shifts, foods,
    students_enrolled, room_capacity,
    food_cost, calories, min_calories=1200,
    adherence_rate=0.7, lambda_weight=0.5, time_limit=120
):
    # Inicializa o solver SCIP (Open-Source, Mixed Integer Programming)
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        print("Solver SCIP não encontrado.")
        return None
    
    # Define o tempo limite em milissegundos
    solver.SetTimeLimit(time_limit * 1000)

    # ==========================================
    # 1. VARIÁVEIS DE DECISÃO
    # ==========================================
    # x[d, r, dia, turno]: 1 se a disciplina 'd' for alocada na sala 'r' no dia/turno
    x = {}
    for d in disciplines:
        for r in rooms:
            for day in days:
                for shift in shifts:
                    x[d, r, day, shift] = solver.IntVar(0, 1, f'x_{d}_{r}_{day}_{shift}')

    # y[m, dia, turno]: Quantidade do alimento 'm' servida no dia/turno
    y = {}
    for m in foods:
        for day in days:
            for shift in shifts:
                # Usando variável contínua para evitar inviabilidade por causa do 0.7 (ex: 24.5 pratos)
                y[m, day, shift] = solver.NumVar(0, solver.infinity(), f'y_{m}_{day}_{shift}')

    # ==========================================
    # 2. RESTRIÇÕES
    # ==========================================
    
    # R1: Cada disciplina deve ser alocada no MÁXIMO uma vez na semana
    for d in disciplines:
        solver.Add(
            solver.Sum([x[d, r, day, shift] for r in rooms for day in days for shift in shifts]) <= 1
        )

    # R2: Capacidade da Sala
    for d in disciplines:
        for r in rooms:
            for day in days:
                for shift in shifts:
                    solver.Add(
                        x[d, r, day, shift] * students_enrolled[d] <= room_capacity[r]
                    )

    # R3: Exclusividade da Sala (No máximo 1 disciplina por sala/turno)
    for r in rooms:
        for day in days:
            for shift in shifts:
                solver.Add(
                    solver.Sum([x[d, r, day, shift] for d in disciplines]) <= 1
                )

    # R4: Acoplamento Educacional-Nutricional (A demanda do RU depende da sala de aula)
    for day in days:
        for shift in shifts:
            # Total de alunos tendo aula neste dia e turno
            z_alunos = solver.Sum([
                x[d, r, day, shift] * students_enrolled[d] 
                for d in disciplines for r in rooms
            ])
            
            # Garantir a oferta de pratos principais baseada na taxa de adesão
            solver.Add(
                y['prato_feito', day, shift] >= z_alunos * adherence_rate
            )
            
            # Garantir a meta calórica mínima
            calorias_oferecidas = solver.Sum([y[m, day, shift] * calories[m] for m in foods])
            calorias_necessarias = (z_alunos * adherence_rate) * min_calories
            solver.Add(calorias_oferecidas >= calorias_necessarias)

    # ==========================================
    # 3. FUNÇÃO OBJETIVO (SOMA PONDERADA)
    # ==========================================
    f1_alunos_cobertos = solver.Sum([
        x[d, r, day, shift] * students_enrolled[d] 
        for d in disciplines for r in rooms for day in days for shift in shifts
    ])
    
    f2_custo_total = solver.Sum([
        y[m, day, shift] * food_cost[m] 
        for m in foods for day in days for shift in shifts
    ])

    # Otimização escalarizada: Minimizar lambda*(-F1) + (1-lambda)*(F2)
    solver.Minimize(lambda_weight * (-f1_alunos_cobertos) + (1.0 - lambda_weight) * f2_custo_total)

    # ==========================================
    # 4. RESOLUÇÃO E EXTRAÇÃO DOS DADOS
    # ==========================================
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        res = {
            'f1_alunos_cobertos': f1_alunos_cobertos.solution_value(),
            'f2_custo_total': f2_custo_total.solution_value()
        }
        return res
    else:
        return None