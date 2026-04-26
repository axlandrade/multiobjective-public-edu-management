import gurobipy as gp
from gurobipy import GRB

def solve_integrated_edu_management(
    disciplines: list, rooms: list, days: list, shifts: list, foods: list,
    students_enrolled: dict, room_capacity: dict, food_cost: dict, calories: dict,
    min_calories: float = 2000, adherence_rate: float = 0.6,
    lambda_weight: float = 0.5, time_limit: int = 3600
):
    """
    Resolve o modelo integrado WSAC-WSMS e retorna as grades e cardápios detalhados.
    Inclui restrições de capacidade, exclusividade física e funcionamento diário.
    """
    with gp.Model("edu_integrated_wsac_wsms") as model:
        
        model.setParam('OutputFlag', 0)
        
        # ==========================================
        # 1. Variáveis de Decisão WSAC (Salas de Aula)
        # ==========================================
        x = model.addVars(disciplines, rooms, days, shifts, vtype=GRB.BINARY, name="x")
        
        # OBRIGATÓRIO: A disciplina tem que ocorrer NO MÁXIMO UMA VEZ
        for i in disciplines:
            model.addConstr(gp.quicksum(x[i, j, k, l] for j in rooms for k in days for l in shifts) <= 1, name=f"disc_once_{i}")
            
        # OBRIGATÓRIO: A turma não pode ser maior que a capacidade da sala
        for i in disciplines:
            for j in rooms:
                for k in days:
                    for l in shifts:
                        model.addConstr(x[i, j, k, l] * students_enrolled[i] <= room_capacity[j], name=f"cap_{i}_{j}_{k}_{l}")

        # EXCLUSIVIDADE: Uma sala só pode ter UMA disciplina por turno/dia
        for j in rooms:
            for k in days:
                for l in shifts:
                    model.addConstr(gp.quicksum(x[i, j, k, l] for i in disciplines) <= 1, name=f"exclusivity_{j}_{k}_{l}")

        # FUNCIONAMENTO MÍNIMO POR TURNO: A universidade federal nunca para
        # Todo dia 'k', em todo turno 'l', deve haver pelo menos 1 aula alocada.
        min_classes_per_shift = 1
        for k in days:
            for l in shifts:
                model.addConstr(
                    gp.quicksum(x[i, j, k, l] for i in disciplines for j in rooms) >= min_classes_per_shift,
                    name=f"min_aulas_turno_{k}_{l}"
                )

        # ==========================================
        # 2. Variáveis de Decisão WSMS (Restaurante Universitário)
        # ==========================================
        y = model.addVars(foods, days, shifts, vtype=GRB.CONTINUOUS, lb=0.0, name="y")
        
        # Calorias mínimas obrigatórias por turno
        for k in days:
            for l in shifts:
                model.addConstr(gp.quicksum(y[f, k, l] * calories[f] for f in foods) >= min_calories, name=f"nutri_{k}_{l}")

        # ==========================================
        # 3. Ponte de Acoplamento WSAC -> WSMS
        # ==========================================
        A = model.addVars(days, shifts, vtype=GRB.INTEGER, name="AlunosAula")
        
        for k in days:
            for l in shifts:
                # Calcula os alunos presentes na universidade naquele turno exato
                model.addConstr(
                    A[k, l] == gp.quicksum(x[i, j, k, l] * students_enrolled[i] for i in disciplines for j in rooms),
                    name=f"alunos_aula_{k}_{l}"
                )
                
                # A quantidade do 'prato_feito' no RU deve cobrir a taxa de adesão dos alunos em aula
                model.addConstr(
                    y['prato_feito', k, l] >= adherence_rate * A[k, l],
                    name=f"acoplamento_ru_{k}_{l}"
                )

        # ==========================================
        # 4. Funções Objetivo (Normalizadas)
        # ==========================================
        f1_cobertura = gp.quicksum(x[i, j, k, l] * students_enrolled[i] for i in disciplines for j in rooms for k in days for l in shifts)
        f2_custo = gp.quicksum(y[f, k, l] * food_cost[f] for f in foods for k in days for l in shifts)
        
        # Normalização empírica para balancear as escalas (0-1) e gerar Pareto viável
        f1_max = sum(students_enrolled[i] for i in disciplines)
        f2_max = 2000.0 # Um valor grande estimado para o orçamento teto do RU
        
        # Evita divisão por zero
        f1_max = f1_max if f1_max > 0 else 1.0
        
        f1_norm = f1_cobertura / f1_max
        f2_norm = f2_custo / f2_max

        # Gurobi minimiza por padrão
        model.ModelSense = GRB.MINIMIZE
        
        # Objetivo Ponderado (-f1 porque queremos maximizar alunos, e +f2 porque queremos minimizar custos)
        model.setObjective(lambda_weight * (-f1_norm) + (1 - lambda_weight) * f2_norm)
        
        # ==========================================
        # 5. Otimização e Extração
        # ==========================================
        model.setParam('TimeLimit', time_limit)
        model.optimize()
        
        if model.Status in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
            schedule = []
            for i in disciplines:
                for j in rooms:
                    for k in days:
                        for l in shifts:
                            if x[i, j, k, l].X > 0.5:
                                schedule.append({
                                    'Dia': k, 'Turno': l, 'Sala': j, 
                                    'Disciplina': i, 'Alunos': students_enrolled[i]
                                })
            menu = []
            for k in days:
                for l in shifts:
                    for f in foods:
                        qtd = y[f, k, l].X
                        if qtd > 0.01:
                            menu.append({
                                'Dia': k, 'Turno': l, 
                                'Item': f, 'Quantidade': round(qtd, 1)
                            })
                            
            return {
                'f1_alunos_cobertos': int(f1_cobertura.getValue()),
                'f2_custo_total': round(f2_custo.getValue(), 2),
                'grade_horaria': schedule,
                'cardapio_ru': menu
            }
        else:
            return None