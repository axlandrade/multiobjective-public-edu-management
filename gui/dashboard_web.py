"""Streamlit web dashboard for the multiobjective management project.

Run with:
    streamlit run gui/dashboard_web.py

The dashboard keeps the project in Python while replacing the previous PySide6
desktop interface with a browser-based workflow for experiments and inspection.
"""

from __future__ import annotations

import json
import random
import re
import time
from pathlib import Path
from typing import Callable

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from deap import tools, algorithms

from src.edu_management.genetic_algorithm import setup_edu_genetic_algorithm
from src.edu_management.optimization_model import solve_integrated_edu_management
from src.public_management.create_real_network import process_and_save_network
from src.public_management.genetic_algorithm import setup_genetic_algorithm
from src.public_management.graph_constructor import build_multigraph_from_csv
from src.public_management.optimization_model import solve_multigraph_cc
from src.public_management.transparency_collector import (
    DEFAULT_INVESTIGATION_CNPJS,
    collect_contracts,
    parse_cnpj_text,
    save_contract_pipeline_outputs,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = DATA_DIR / "dashboard_uploads"
RESULTS_DIR = ROOT_DIR / "results_dashboard"
TRANSPARENCY_DIR = DATA_DIR / "portal_transparencia"
LAST_NETWORK_STATE_KEY = "latest_network_csv_path"


def configure_page() -> None:
    """Apply Streamlit page settings and compact dashboard styling."""
    st.set_page_config(
        page_title="Gestao multiobjetivo",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
        [data-testid="stMetricValue"] {font-size: 1.6rem;}
        [data-testid="stSidebar"] {min-width: 310px;}
        div[data-testid="stDataFrame"] {border: 1px solid #e7e7e7; border-radius: 6px;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def sanitize_filename(name: str) -> str:
    """Create a filesystem-safe name for uploaded CSV files."""
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip())
    return clean or "uploaded.csv"


def save_uploaded_csv(uploaded_file) -> Path | None:
    """Persist a Streamlit uploaded CSV in the local data folder."""
    if uploaded_file is None:
        return None
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_DIR / sanitize_filename(uploaded_file.name)
    target.write_bytes(uploaded_file.getbuffer())
    return target


def resolve_data_source(uploaded_file, typed_path: str) -> Path | None:
    """Return either the uploaded CSV path or a manually provided local path."""
    uploaded_path = save_uploaded_csv(uploaded_file)
    if uploaded_path:
        return uploaded_path
    if typed_path.strip():
        return Path(typed_path.strip())
    return None


def remember_network_path(path: str | Path) -> None:
    """Store the latest generated network path for reuse across dashboard tabs."""
    st.session_state[LAST_NETWORK_STATE_KEY] = str(path)


def latest_network_path() -> Path | None:
    """Return the latest generated network path when it still exists."""
    value = st.session_state.get(LAST_NETWORK_STATE_KEY)
    if not value:
        return None
    path = Path(value)
    return path if path.exists() else None


def network_download_button(path: Path, label: str = "Baixar rede real CSV") -> None:
    """Render a download button for a generated model-ready network CSV."""
    st.download_button(
        label,
        path.read_bytes(),
        file_name=path.name,
        mime="text/csv",
    )


def graph_summary(G: nx.Graph) -> dict[str, float]:
    """Compute simple graph indicators for dashboard metric cards."""
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "density": nx.density(nx.Graph(G)) if G.number_of_nodes() > 1 else 0.0,
        "components": nx.number_connected_components(nx.Graph(G)) if G.number_of_nodes() else 0,
    }


def draw_graph(G: nx.MultiGraph, clusters: dict | None = None, max_nodes: int = 80) -> go.Figure:
    """Create an interactive Plotly network figure from a NetworkX graph."""
    if G.number_of_nodes() > max_nodes:
        degrees = dict(G.degree())
        selected = sorted(degrees, key=degrees.get, reverse=True)[:max_nodes]
        H = G.subgraph(selected).copy()
    else:
        H = G.copy()

    simple = nx.Graph()
    for u, v, data in H.edges(data=True):
        risk = data.get("positive_prob", data.get("weight", 0.5))
        if simple.has_edge(u, v):
            simple[u][v]["weight"] += 1
            simple[u][v]["risk_sum"] += risk
        else:
            simple.add_edge(u, v, weight=1, risk_sum=risk)
    simple.add_nodes_from(H.nodes())

    pos = nx.spring_layout(simple, seed=42, k=0.8) if simple.number_of_nodes() else {}

    edge_x, edge_y = [], []
    for u, v, data in simple.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1, color="#9aa0a6"),
        hoverinfo="none",
        mode="lines",
    )

    node_x, node_y, node_label, node_color, node_size = [], [], [], [], []
    degrees = dict(simple.degree())
    for node in simple.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_label.append(str(node))
        node_size.append(12 + min(degrees.get(node, 0), 20) * 2)
        node_color.append(str(clusters.get(node, node)) if clusters else str(node))

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_label,
        textposition="top center",
        hovertext=node_label,
        hoverinfo="text",
        marker=dict(size=node_size, color=pd.factorize(node_color)[0], colorscale="Viridis"),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        height=560,
        margin=dict(l=0, r=0, t=24, b=0),
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
    )
    return fig


def public_data_controls(prefix: str) -> Path | None:
    """Render shared data-source controls for public-management tabs."""
    latest_path = latest_network_path()
    if latest_path:
        st.success(f"Rede real gerada disponivel: {latest_path}")
        c1, c2 = st.columns([0.45, 0.55])
        with c1:
            use_latest = st.checkbox("Usar rede real gerada", value=True, key=f"{prefix}_use_latest")
        with c2:
            network_download_button(latest_path, "Baixar rede real")
        if use_latest:
            return latest_path

    uploaded = st.file_uploader("CSV de rede ou contratos", type=["csv"], key=f"{prefix}_upload")
    typed_path = st.text_input("Ou informe um caminho local", value="", key=f"{prefix}_path")
    return resolve_data_source(uploaded, typed_path)


def render_public_exact() -> None:
    """Run the exact OR-Tools public-management model from the dashboard."""
    st.subheader("Gestao publica: modelo exato")
    data_path = public_data_controls("public_exact")
    lambda_weight = st.slider("Lambda", 0.0, 1.0, 0.5, 0.05, key="exact_lambda")
    time_limit = st.number_input("Limite de tempo do solver (s)", 10, 7200, 120, step=10)

    if st.button("Executar modelo exato", type="primary", disabled=data_path is None):
        with st.status("Preparando grafo e resolvendo modelo...", expanded=True):
            G = build_multigraph_from_csv(str(data_path))
            if not G:
                st.error("Nao foi possivel carregar o grafo.")
                return
            summary = graph_summary(G)
            st.write(f"Grafo: {summary['nodes']} nos, {summary['edges']} arestas.")
            result = solve_multigraph_cc(G, lambda_weight=lambda_weight, time_limit=int(time_limit))

        if not result or not result[0]:
            st.warning("O solver nao encontrou solucao viavel no tempo definido.")
            return

        clusters, obj_val, exec_time, f1_disagreement, f2_num_clusters = result
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Objetivo Z", f"{obj_val:.4f}")
        c2.metric("Desequilibrio f1", f"{f1_disagreement:.4f}")
        c3.metric("Clusters f2", int(f2_num_clusters))
        c4.metric("Tempo solver", f"{exec_time:.2f}s")

        df_clusters = pd.DataFrame(
            list(clusters.items()),
            columns=["node", "cluster_representative"],
        ).sort_values(["cluster_representative", "node"])

        left, right = st.columns([0.44, 0.56])
        with left:
            st.dataframe(df_clusters, use_container_width=True, hide_index=True)
            st.download_button(
                "Baixar clusters CSV",
                df_clusters.to_csv(index=False).encode("utf-8"),
                file_name="clusters_exato.csv",
                mime="text/csv",
            )
        with right:
            st.plotly_chart(draw_graph(G, clusters), use_container_width=True)


def run_public_ga(
    data_path: Path,
    pop_size: int,
    ngen: int,
    cxpb: float,
    mutpb: float,
    progress_callback: Callable[[int, str], None],
) -> tuple[pd.DataFrame, dict, dict]:
    """Execute a compact NSGA-II run and return scores, partitions, and stats."""
    G = build_multigraph_from_csv(str(data_path))
    if not G:
        raise ValueError("Nao foi possivel carregar o grafo.")

    nodes = sorted(list(G.nodes()))
    toolbox = setup_genetic_algorithm(nodes, G)
    population = toolbox.population(n=pop_size)
    pareto_front = tools.ParetoFront()
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("min", np.min, axis=0)

    start = time.time()
    fitnesses = list(map(toolbox.evaluate, population))
    for ind, fit in zip(population, fitnesses):
        ind.fitness.values = fit
    pareto_front.update(population)

    for generation in range(1, ngen + 1):
        offspring = toolbox.select(population, len(population))
        offspring = algorithms.varAnd(offspring, toolbox, cxpb, mutpb)
        invalid = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = list(map(toolbox.evaluate, invalid))
        for ind, fit in zip(invalid, fitnesses):
            ind.fitness.values = fit
        pareto_front.update(offspring)
        population[:] = toolbox.select(population + offspring, pop_size)
        record = stats.compile(population)
        progress_callback(
            generation,
            f"Geracao {generation}/{ngen} | min f1={record['min'][0]:.2f}, min f2={record['min'][1]:.0f}",
        )

    pareto_rows, partitions = [], {}
    for idx, individual in enumerate(pareto_front):
        solution_id = f"solution_{idx}"
        f1_disagreement, f2_clusters = individual.fitness.values
        pareto_rows.append(
            {
                "solution_id": solution_id,
                "num_clusters_f2": int(f2_clusters),
                "disagreement_f1": f1_disagreement,
            }
        )
        partitions[solution_id] = list(individual)

    df_pareto = (
        pd.DataFrame(pareto_rows)
        .sort_values(["num_clusters_f2", "disagreement_f1"])
        .drop_duplicates()
        .reset_index(drop=True)
    )
    run_stats = {
        "nodes": len(nodes),
        "edges": G.number_of_edges(),
        "total_execution_time_seconds": round(time.time() - start, 2),
        "num_pareto_solutions": len(df_pareto),
    }
    return df_pareto, partitions, run_stats


def render_public_heuristic() -> None:
    """Run the public-management NSGA-II heuristic from the dashboard."""
    st.subheader("Gestao publica: heuristica NSGA-II")
    data_path = public_data_controls("public_ga")
    c1, c2, c3, c4 = st.columns(4)
    pop_size = c1.number_input("Populacao", 20, 5000, 120, step=20)
    ngen = c2.number_input("Geracoes", 5, 2000, 80, step=5)
    cxpb = c3.slider("Crossover", 0.0, 1.0, 0.5, 0.05)
    mutpb = c4.slider("Mutacao", 0.0, 1.0, 0.3, 0.05)

    if st.button("Executar NSGA-II", type="primary", disabled=data_path is None):
        progress = st.progress(0, text="Iniciando evolucao...")

        def update_progress(generation: int, text: str) -> None:
            progress.progress(generation / ngen, text=text)

        try:
            df_pareto, partitions, run_stats = run_public_ga(
                Path(data_path),
                int(pop_size),
                int(ngen),
                float(cxpb),
                float(mutpb),
                update_progress,
            )
        except Exception as exc:
            st.error(str(exc))
            return

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        df_pareto.to_csv(RESULTS_DIR / "pareto_public_management.csv", index=False)
        (RESULTS_DIR / "partitions_public_management.json").write_text(
            json.dumps(partitions, indent=2),
            encoding="utf-8",
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Solucoes Pareto", run_stats["num_pareto_solutions"])
        c2.metric("Nos", run_stats["nodes"])
        c3.metric("Tempo", f"{run_stats['total_execution_time_seconds']}s")

        left, right = st.columns([0.48, 0.52])
        with left:
            st.dataframe(df_pareto, use_container_width=True, hide_index=True)
            st.download_button(
                "Baixar Pareto CSV",
                df_pareto.to_csv(index=False).encode("utf-8"),
                file_name="pareto_public_management.csv",
                mime="text/csv",
            )
        with right:
            fig = px.scatter(
                df_pareto,
                x="num_clusters_f2",
                y="disagreement_f1",
                hover_name="solution_id",
                title="Fronteira de Pareto aproximada",
            )
            st.plotly_chart(fig, use_container_width=True)


def build_edu_demo_instance() -> dict:
    """Create the synthetic university instance used by the experiment scripts."""
    random.seed(42)
    disciplines = [f"Disc_{i:02d}" for i in range(1, 21)]
    return {
        "disciplines": disciplines,
        "rooms": ["Sala_101", "Sala_102", "Sala_103", "Lab_01", "Auditorio"],
        "days": ["Segunda", "Terca", "Quarta", "Quinta", "Sexta"],
        "shifts": ["Manha", "Tarde", "Noite"],
        "foods": ["prato_feito", "salada_extra", "suco", "sobremesa"],
        "students_enrolled": {d: random.randint(20, 90) for d in disciplines},
        "room_capacity": {
            "Sala_101": 40,
            "Sala_102": 40,
            "Sala_103": 50,
            "Lab_01": 30,
            "Auditorio": 100,
        },
        "food_cost": {"prato_feito": 8.50, "salada_extra": 2.00, "suco": 1.50, "sobremesa": 3.00},
        "calories": {"prato_feito": 800, "salada_extra": 100, "suco": 150, "sobremesa": 250},
    }


def decode_edu_individual(
    individual,
    disciplines: list[str],
    slots: list[dict],
    students_enrolled: dict[str, int],
    food_cost: dict[str, float],
    calories: dict[str, float],
    *,
    min_calories: float = 1200,
    adherence_rate: float = 0.7,
) -> dict:
    """Decode an educational GA chromosome into managerial metrics and schedule."""
    schedule = []
    students_by_shift = {}
    used_slots = set()
    valid = True

    for idx_disc, slot_id in enumerate(individual):
        if slot_id == -1:
            continue
        if slot_id in used_slots:
            valid = False
            break
        used_slots.add(slot_id)

        discipline = disciplines[idx_disc]
        slot = slots[slot_id]
        students = students_enrolled[discipline]
        schedule.append({
            "Dia": slot["Dia"],
            "Turno": slot["Turno"],
            "Sala": slot["Sala"],
            "Disciplina": discipline,
            "Alunos": students,
        })
        key = (slot["Dia"], slot["Turno"])
        students_by_shift[key] = students_by_shift.get(key, 0) + students

    if not valid:
        return {"valid": False}

    menu = []
    total_cost = 0.0
    for day in sorted({slot["Dia"] for slot in slots}):
        for shift in sorted({slot["Turno"] for slot in slots}):
            students = students_by_shift.get((day, shift), 0)
            meals = int(students * adherence_rate)
            shift_cost = meals * food_cost["prato_feito"]
            calories_served = meals * calories["prato_feito"]

            if meals:
                menu.append({"Dia": day, "Turno": shift, "Item": "prato_feito", "Quantidade": meals})

            missing_calories = min_calories - calories_served
            if missing_calories > 0:
                salad_servings = missing_calories / calories["salada_extra"]
                shift_cost += salad_servings * food_cost["salada_extra"]
                menu.append({
                    "Dia": day,
                    "Turno": shift,
                    "Item": "salada_extra",
                    "Quantidade": round(salad_servings, 2),
                })

            total_cost += shift_cost

    return {
        "valid": True,
        "f1_alunos": int(sum(item["Alunos"] for item in schedule)),
        "f2_custo_ru": round(total_cost, 2),
        "grade_horaria": schedule,
        "cardapio_ru": menu,
    }


def render_edu_exact() -> None:
    """Run the integrated educational OR-Tools model for multiple lambdas."""
    st.subheader("Gestao educacional: varredura exata")
    instance = build_edu_demo_instance()
    lambda_text = st.text_input("Valores lambda", "0.0, 0.25, 0.5, 0.75, 1.0")
    time_limit = st.number_input("Limite por lambda (s)", 10, 7200, 120, step=10)

    st.caption(
        f"Cenario: {len(instance['disciplines'])} disciplinas, "
        f"{len(instance['rooms'])} salas, {sum(instance['students_enrolled'].values())} alunos."
    )

    if st.button("Executar varredura educacional", type="primary"):
        lambdas = [float(value.strip()) for value in lambda_text.split(",") if value.strip()]
        rows = []
        details = {}
        progress = st.progress(0, text="Iniciando varredura...")

        for idx, lambda_weight in enumerate(lambdas, start=1):
            progress.progress(idx / len(lambdas), text=f"Lambda {lambda_weight}...")
            start = time.time()
            result = solve_integrated_edu_management(
                disciplines=instance["disciplines"],
                rooms=instance["rooms"],
                days=instance["days"],
                shifts=instance["shifts"],
                foods=instance["foods"],
                students_enrolled=instance["students_enrolled"],
                room_capacity=instance["room_capacity"],
                food_cost=instance["food_cost"],
                calories=instance["calories"],
                min_calories=1200,
                adherence_rate=0.7,
                lambda_weight=lambda_weight,
                time_limit=int(time_limit),
            )
            if result:
                solution_id = f"lambda_{lambda_weight:g}"
                rows.append(
                    {
                        "solution_id": solution_id,
                        "lambda": lambda_weight,
                        "f1_alunos": int(result["f1_alunos_cobertos"]),
                        "f2_custo_ru": round(result["f2_custo_total"], 2),
                        "tempo_execucao_s": round(time.time() - start, 2),
                    }
                )
                details[solution_id] = {
                    "grade_horaria": result.get("grade_horaria", []),
                    "cardapio_ru": result.get("cardapio_ru", []),
                }

        if not rows:
            st.warning("Nenhuma solucao foi encontrada.")
            return

        df = pd.DataFrame(rows)
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(RESULTS_DIR / "pareto_edu_exact.csv", index=False)

        left, right = st.columns([0.45, 0.55])
        with left:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                "Baixar varredura CSV",
                df.to_csv(index=False).encode("utf-8"),
                file_name="pareto_edu_exact.csv",
                mime="text/csv",
            )
            st.download_button(
                "Baixar detalhes JSON",
                json.dumps(details, indent=2, ensure_ascii=False).encode("utf-8"),
                file_name="detalhes_edu_exact.json",
                mime="application/json",
            )
        with right:
            fig = px.line(
                df,
                x="f2_custo_ru",
                y="f1_alunos",
                text="lambda",
                markers=True,
                title="Trade-off cobertura discente x custo RU",
            )
            st.plotly_chart(fig, use_container_width=True)

        selected_solution = st.selectbox("Inspecionar solucao", list(details.keys()))
        if selected_solution:
            grade_df = pd.DataFrame(details[selected_solution]["grade_horaria"])
            menu_df = pd.DataFrame(details[selected_solution]["cardapio_ru"])
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Grade WSAC**")
                st.dataframe(grade_df, use_container_width=True, hide_index=True)
            with c2:
                st.markdown("**Cardapio WSMS**")
                st.dataframe(menu_df, use_container_width=True, hide_index=True)


def run_edu_ga(
    instance: dict,
    pop_size: int,
    ngen: int,
    cxpb: float,
    mutpb: float,
    progress_callback: Callable[[int, str], None],
) -> tuple[pd.DataFrame, dict]:
    """Run the educational NSGA-II model and return Pareto metrics plus details."""
    toolbox, slots = setup_edu_genetic_algorithm(
        disciplines=instance["disciplines"],
        rooms=instance["rooms"],
        days=instance["days"],
        shifts=instance["shifts"],
        students_enrolled=instance["students_enrolled"],
        food_cost=instance["food_cost"],
        calories=instance["calories"],
        min_calories=1200,
        adherence_rate=0.7,
    )

    population = toolbox.population(n=pop_size)
    pareto_front = tools.ParetoFront()
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("min", np.min, axis=0)

    fitnesses = list(map(toolbox.evaluate, population))
    for ind, fit in zip(population, fitnesses):
        ind.fitness.values = fit
    pareto_front.update(population)

    for generation in range(1, ngen + 1):
        offspring = toolbox.select(population, len(population))
        offspring = algorithms.varAnd(offspring, toolbox, cxpb, mutpb)
        invalid = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = list(map(toolbox.evaluate, invalid))
        for ind, fit in zip(invalid, fitnesses):
            ind.fitness.values = fit
        pareto_front.update(offspring)
        population[:] = toolbox.select(population + offspring, pop_size)
        record = stats.compile(population)
        progress_callback(generation, f"Geracao {generation}/{ngen} | min={record['min']}")

    rows = []
    details = {}
    for idx, individual in enumerate(pareto_front):
        decoded = decode_edu_individual(
            individual,
            instance["disciplines"],
            slots,
            instance["students_enrolled"],
            instance["food_cost"],
            instance["calories"],
        )
        if not decoded.get("valid") or decoded["f1_alunos"] == 0:
            continue
        solution_id = f"NSGA_{idx:03d}"
        rows.append({
            "solution_id": solution_id,
            "f1_alunos": decoded["f1_alunos"],
            "f2_custo_ru": decoded["f2_custo_ru"],
            "cromossomo": list(individual),
        })
        details[solution_id] = {
            "grade_horaria": decoded["grade_horaria"],
            "cardapio_ru": decoded["cardapio_ru"],
        }

    if not rows:
        return pd.DataFrame(), {}

    df = (
        pd.DataFrame(rows)
        .sort_values(["f1_alunos", "f2_custo_ru"])
        .drop_duplicates(subset=["f1_alunos", "f2_custo_ru"])
        .reset_index(drop=True)
    )
    return df, details


def render_edu_heuristic() -> None:
    """Run the integrated educational NSGA-II model from the dashboard."""
    st.subheader("Gestao educacional: WSAC + WSMS via NSGA-II")
    instance = build_edu_demo_instance()
    st.caption(
        f"Cenario sintetico: {len(instance['disciplines'])} disciplinas, "
        f"{len(instance['rooms'])} salas, {sum(instance['students_enrolled'].values())} alunos."
    )

    c1, c2, c3, c4 = st.columns(4)
    pop_size = c1.number_input("Populacao", 20, 3000, 200, step=20, key="edu_pop")
    ngen = c2.number_input("Geracoes", 5, 1500, 150, step=5, key="edu_gen")
    cxpb = c3.slider("Crossover", 0.0, 1.0, 0.5, 0.05, key="edu_cx")
    mutpb = c4.slider("Mutacao", 0.0, 1.0, 0.3, 0.05, key="edu_mut")

    if st.button("Executar NSGA-II educacional", type="primary"):
        progress = st.progress(0, text="Iniciando evolucao educacional...")

        def update_progress(generation: int, text: str) -> None:
            progress.progress(generation / int(ngen), text=text)

        start = time.time()
        df, details = run_edu_ga(
            instance,
            int(pop_size),
            int(ngen),
            float(cxpb),
            float(mutpb),
            update_progress,
        )

        if df.empty:
            st.warning("Nenhuma solucao valida foi encontrada.")
            return

        c1, c2 = st.columns(2)
        c1.metric("Solucoes Pareto", len(df))
        c2.metric("Tempo", f"{time.time() - start:.2f}s")

        left, right = st.columns([0.45, 0.55])
        with left:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                "Baixar Pareto educacional CSV",
                df.to_csv(index=False).encode("utf-8"),
                file_name="pareto_edu_nsga2.csv",
                mime="text/csv",
            )
            st.download_button(
                "Baixar detalhes JSON",
                json.dumps(details, indent=2, ensure_ascii=False).encode("utf-8"),
                file_name="detalhes_edu_nsga2.json",
                mime="application/json",
            )
        with right:
            fig = px.scatter(
                df,
                x="f2_custo_ru",
                y="f1_alunos",
                hover_name="solution_id",
                title="Fronteira WSAC + WSMS aproximada",
            )
            st.plotly_chart(fig, use_container_width=True)

        selected_solution = st.selectbox("Inspecionar solucao NSGA-II", list(details.keys()))
        if selected_solution:
            grade_df = pd.DataFrame(details[selected_solution]["grade_horaria"])
            menu_df = pd.DataFrame(details[selected_solution]["cardapio_ru"])
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Grade WSAC**")
                st.dataframe(grade_df, use_container_width=True, hide_index=True)
            with c2:
                st.markdown("**Cardapio WSMS**")
                st.dataframe(menu_df, use_container_width=True, hide_index=True)


def render_real_data_processing() -> None:
    """Collect/enrich Portal data or convert uploaded contracts to network CSV."""
    st.subheader("Portal da Transparencia e rede de contratos")
    existing_network = latest_network_path()
    if existing_network:
        st.info(f"Ultima rede real gerada: {existing_network}")
        network_download_button(existing_network)

    mode = st.radio(
        "Origem dos dados",
        ["Coletar pela API", "Converter CSV enriquecido"],
        horizontal=True,
    )

    if mode == "Converter CSV enriquecido":
        uploaded = st.file_uploader("CSV enriquecido de contratos", type=["csv"], key="contracts_upload")
        default_output = DATA_DIR / "rede_real_input_dashboard.csv"
        output_path = st.text_input("Arquivo de saida da rede", str(default_output))

        if st.button("Gerar rede", disabled=uploaded is None):
            input_path = save_uploaded_csv(uploaded)
            try:
                rows = process_and_save_network(str(input_path), output_path)
            except Exception as exc:
                st.error(str(exc))
                return
            remember_network_path(output_path)
            st.success(f"Rede salva em {output_path} com {rows} arestas.")
            network_download_button(Path(output_path))
        return

    st.caption(
        "Cole sua chave da API de Dados Abertos do Portal da Transparencia e os CNPJs de interesse. "
        "O dashboard salva contratos brutos, contratos enriquecidos e a rede pronta para o modelo."
    )
    api_key = st.text_input("Chave da API", type="password")
    use_default_list = st.checkbox("Usar lista padrao da investigacao", value=True)
    default_cnpj_text = "\n".join(DEFAULT_INVESTIGATION_CNPJS[:10])
    cnpj_text = st.text_area(
        "CNPJs para coleta",
        value="\n".join(DEFAULT_INVESTIGATION_CNPJS) if use_default_list else default_cnpj_text,
        height=220,
    )

    c1, c2, c3 = st.columns(3)
    max_pages = c1.number_input("Max. paginas por CNPJ (0 = todas)", 0, 500, 0, step=1)
    delay = c2.number_input("Pausa entre paginas (s)", 0.0, 5.0, 0.5, step=0.1)
    output_folder = c3.text_input("Pasta de saida", str(TRANSPARENCY_DIR))

    cnpjs = parse_cnpj_text(cnpj_text)
    st.write(f"CNPJs validos identificados: **{len(cnpjs)}**")

    if st.button("Coletar, enriquecer e gerar rede", type="primary", disabled=not api_key or not cnpjs):
        status_box = st.empty()

        def update_status(message: str) -> None:
            status_box.info(message)

        try:
            raw_df = collect_contracts(
                cnpjs,
                api_key,
                request_delay=float(delay),
                max_pages_per_cnpj=None if int(max_pages) == 0 else int(max_pages),
                progress_callback=update_status,
            )
        except Exception as exc:
            st.error(str(exc))
            return

        if raw_df.empty:
            st.warning("Nenhum contrato foi encontrado para os CNPJs informados.")
            return

        raw_path, enriched_path, enriched_df = save_contract_pipeline_outputs(raw_df, output_folder)
        network_path = Path(output_folder) / "rede_real_input.csv"
        try:
            edge_count = process_and_save_network(str(enriched_path), str(network_path))
        except Exception as exc:
            st.error(f"Contratos coletados, mas a rede nao foi gerada: {exc}")
            return
        remember_network_path(network_path)

        st.success(f"Coleta concluida: {len(raw_df)} contratos, {edge_count} arestas na rede.")
        m1, m2, m3 = st.columns(3)
        m1.metric("Contratos brutos", len(raw_df))
        m2.metric("Linhas enriquecidas", len(enriched_df))
        m3.metric("Arestas da rede", edge_count)

        st.write("Arquivos gerados:")
        st.code(f"{raw_path}\n{enriched_path}\n{network_path}", language="text")
        st.dataframe(enriched_df.head(50), use_container_width=True, hide_index=True)

        st.download_button(
            "Baixar contratos enriquecidos",
            enriched_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="contratos_enriquecidos.csv",
            mime="text/csv",
        )
        network_download_button(network_path, "Baixar rede real para upload/modelo")


def render_home() -> None:
    """Render project overview cards and practical instructions."""
    st.title("Dashboard web de gestao multiobjetivo")
    st.write(
        "Interface web para executar e inspecionar modelos de gestao publica e "
        "gestao educacional sem depender da antiga GUI desktop."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Framework recomendado", "Streamlit")
    c2.metric("Solver ativo", "OR-Tools/SCIP")
    c3.metric("Heuristica", "NSGA-II")

    st.info(
        "Use a barra lateral para escolher o fluxo. Resultados gerados pela "
        "dashboard sao salvos em results_dashboard/."
    )


def main() -> None:
    """Streamlit application entry point."""
    configure_page()

    with st.sidebar:
        st.title("Navegacao")
        page = st.radio(
            "Modulo",
            [
                "Visao geral",
                "Processar contratos",
                "Publica - exato",
                "Publica - NSGA-II",
                "Educacional - exato",
                "Educacional - NSGA-II",
            ],
        )

    if page == "Visao geral":
        render_home()
    elif page == "Processar contratos":
        render_real_data_processing()
    elif page == "Publica - exato":
        render_public_exact()
    elif page == "Publica - NSGA-II":
        render_public_heuristic()
    elif page == "Educacional - exato":
        render_edu_exact()
    elif page == "Educacional - NSGA-II":
        render_edu_heuristic()


if __name__ == "__main__":
    main()
