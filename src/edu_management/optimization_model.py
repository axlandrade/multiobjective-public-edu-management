"""Exact OR-Tools model for the integrated educational-management problem.

The formulation couples classroom allocation (WSAC) with university-restaurant
meal planning (WSMS). Lambda controls the trade-off between covering more
students and reducing the total meal cost.
"""

# src/edu_management/optimization_model.py

from ortools.linear_solver import pywraplp

def solve_integrated_edu_management(
    disciplines, rooms, days, shifts, foods,
    students_enrolled, room_capacity,
    food_cost, calories, min_calories=1200,
    adherence_rate=0.7, lambda_weight=0.5, time_limit=120
):
    """Solve the integrated WSAC-WSMS weighted model and return objective values."""
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        return None
    solver.SetTimeLimit(time_limit * 1000)

    # ==========================================
    # 1. VARIÁVEIS DE DECISÃO (COM LIMITES)
    # ==========================================
    x = {}
    # Each discipline can be scheduled at most once.
    for d in disciplines:
        for r in rooms:
            for day in days:
                for shift in shifts:
                    x[d, r, day, shift] = solver.IntVar(0, 1, f'x_{d}_{r}_{day}_{shift}')

    y = {}
    # LIMITE: O RU nunca fará mais que 2000 refeições de um mesmo item num único turno.
    # Isso resolve o bug do infinito no lambda = 1.0
    for m in foods:
        for day in days:
            for shift in shifts:
                y[m, day, shift] = solver.NumVar(0, 2000, f'y_{m}_{day}_{shift}')

    # ==========================================
    # 2. RESTRIÇÕES (Iguais)
    # ==========================================
    # Capacity constraints prevent allocating a class to a room that is too small.
    for d in disciplines:
        solver.Add(solver.Sum([x[d, r, day, shift] for r in rooms for day in days for shift in shifts]) <= 1)

    for d in disciplines:
        for r in rooms:
            for day in days:
                for shift in shifts:
                    solver.Add(x[d, r, day, shift] * students_enrolled[d] <= room_capacity[r])

    # A physical room cannot host more than one discipline in the same slot.
    for r in rooms:
        for day in days:
            for shift in shifts:
                solver.Add(solver.Sum([x[d, r, day, shift] for d in disciplines]) <= 1)

    # Coupling constraints: scheduled students generate restaurant demand.
    for day in days:
        for shift in shifts:
            z_alunos = solver.Sum([x[d, r, day, shift] * students_enrolled[d] for d in disciplines for r in rooms])
            solver.Add(y['prato_feito', day, shift] >= z_alunos * adherence_rate)
            
            calorias_oferecidas = solver.Sum([y[m, day, shift] * calories[m] for m in foods])
            calorias_necessarias = (z_alunos * adherence_rate) * min_calories
            solver.Add(calorias_oferecidas >= calorias_necessarias)

    # ==========================================
    # 3. FUNÇÃO OBJETIVO NORMALIZADA
    # ==========================================
    f1_alunos_cobertos = solver.Sum([
        x[d, r, day, shift] * students_enrolled[d] 
        for d in disciplines for r in rooms for day in days for shift in shifts
    ])
    
    f2_custo_total = solver.Sum([
        y[m, day, shift] * food_cost[m] 
        for m in foods for day in days for shift in shifts
    ])

    # NORMALIZAÇÃO: Dividimos alunos por 1000 e custo por 10000 para que ambos variem de ~0.0 a 1.0.
    # Adicionamos + 0.0001 no peso do custo apenas para impedir que o solver ignore totalmente o custo no lambda=1.0
    # Normalization keeps both objectives on comparable numerical scales.
    peso_alunos = lambda_weight
    peso_custo = max(1.0 - lambda_weight, 0.0001)

    solver.Minimize(
        peso_alunos * (-f1_alunos_cobertos / 1000.0) + peso_custo * (f2_custo_total / 10000.0)
    )

    # ==========================================
    # 4. RESOLUÇÃO E EXTRAÇÃO DOS DADOS
    # ==========================================
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        schedule = []
        for d in disciplines:
            for r in rooms:
                for day in days:
                    for shift in shifts:
                        if x[d, r, day, shift].solution_value() > 0.5:
                            schedule.append({
                                'Dia': day,
                                'Turno': shift,
                                'Sala': r,
                                'Disciplina': d,
                                'Alunos': students_enrolled[d],
                            })

        menu = []
        for day in days:
            for shift in shifts:
                for food in foods:
                    quantity = y[food, day, shift].solution_value()
                    if quantity > 0.01:
                        menu.append({
                            'Dia': day,
                            'Turno': shift,
                            'Item': food,
                            'Quantidade': round(quantity, 2),
                        })

        return {
            'f1_alunos_cobertos': f1_alunos_cobertos.solution_value(),
            'f2_custo_total': f2_custo_total.solution_value(),
            'grade_horaria': schedule,
            'cardapio_ru': menu,
        }
    else:
        return None
