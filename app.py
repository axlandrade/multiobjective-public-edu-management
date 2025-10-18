# app.py

from experiments.heuristic.run_genetic_algorithm import run_ga_experiment
from src.optimization_model import solve_multigraph_cc
from src.graph_constructor import build_multigraph_from_csv
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys
import time

# --- CONFIGURAÇÃO DE PATH ---
# Adiciona a pasta raiz ao path para que possamos importar de 'src' e 'experiments'
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- IMPORTAÇÕES DAS FUNÇÕES DO PROJETO ---

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Análise de Redes de Corrupção", layout="wide")

st.title("Dashboard de Análise de Redes de Corrupção")
st.write("Interface unificada para execução dos modelos Exato (Gurobi) e Heurístico (AG).")

# --- BARRA LATERAL (INPUTS) ---
with st.sidebar:
    st.header("1. Configuração do Experimento")

    uploaded_file = st.file_uploader(
        "Selecione o arquivo da rede (.csv)", type="csv")

    analysis_type = st.radio(
        "**Tipo de Análise**",
        ["Heurística (Algoritmo Genético)", "Exata (Gurobi/PLI)"]
    )

    st.markdown("---")

    # Parâmetros condicionais
    if analysis_type == "Heurística (Algoritmo Genético)":
        st.subheader("Parâmetros do Algoritmo Genético")
        pop_size = st.slider("Tamanho da População", 100, 5000, 2000, 100)
        ngen = st.slider("Número de Gerações", 50, 2000, 1000, 50)
        cxpb = st.slider("Prob. de Crossover", 0.0, 1.0, 0.5, 0.1)
        mutpb = st.slider("Prob. de Mutação", 0.0, 1.0, 0.5, 0.1)
    else:  # Exata
        st.subheader("Parâmetros do Modelo Exato")
        lambda_weight = st.slider("Peso Lambda (λ)", 0.0, 1.0, 0.5, 0.05)
        time_limit = st.number_input(
            "Limite de Tempo (segundos)", min_value=60, value=3600)

    run_button = st.button(
        "Executar Análise", type="primary", disabled=(not uploaded_file))

# --- ÁREA PRINCIPAL (OUTPUTS) ---
st.header("2. Resultados")

if run_button:
    # Salva o arquivo temporariamente para os scripts lerem
    data_path = "temp_network_ui.csv"
    with open(data_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if analysis_type == "Heurística (Algoritmo Genético)":
        with st.spinner(f"Executando o Algoritmo Genético por {ngen} gerações... Isso pode levar vários minutos."):
            stats, pareto_df, partitions = run_ga_experiment(
                data_path=data_path, output_dir="results_ui_ga",
                pop_size=pop_size, ngen=ngen, cxpb=cxpb, mutpb=mutpb
            )
            st.session_state.results_type = "heuristic"
            st.session_state.results = (stats, pareto_df, partitions)
            st.success("Análise heurística concluída!")

    else:  # Exata
        with st.spinner(f"Executando o Modelo Exato com limite de {time_limit}s... Por favor, aguarde."):
            G = build_multigraph_from_csv(data_path)
            if G:
                clusters, obj_val, exec_time, f1, f2 = solve_multigraph_cc(
                    G, lambda_weight=lambda_weight, time_limit=time_limit
                )
                stats = {'exec_time': exec_time, 'f1': f1, 'f2': f2}
                st.session_state.results_type = "exact"
                st.session_state.results = (stats, clusters)
                st.success("Análise exata concluída!")
            else:
                st.error("Falha ao carregar o grafo.")

# Exibe os resultados salvos na sessão
if 'results' in st.session_state:
    if st.session_state.results_type == "heuristic":
        stats, pareto_df, partitions = st.session_state.results

        st.subheader("Sumário da Execução (AG)")
        col1, col2 = st.columns(2)
        col1.metric("Tempo Total (min)", stats['total_execution_time_minutes'])
        col2.metric("Nº de Soluções na Fronteira",
                    stats['num_pareto_solutions'])

        st.subheader("Fronteira de Pareto Interativa")
        fig = px.scatter(
            pareto_df, x='num_clusters_f2', y='disagreement_f1',
            title='Trade-off: Desequilíbrio vs. Número de Clusters',
            labels={
                'num_clusters_f2': 'Número de Clusters (f2)', 'disagreement_f1': 'Desequilíbrio (f1)'},
            hover_data=['solution_id']
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(pareto_df)

    elif st.session_state.results_type == "exact":
        stats, clusters = st.session_state.results
        if clusters:
            st.subheader("Resultado da Execução (Exata)")
            col1, col2, col3 = st.columns(3)
            col1.metric("Tempo do Solver (s)", f"{stats['exec_time']:.2f}")
            col2.metric("Desequilíbrio (f1)", f"{stats['f1']:.4f}")
            col3.metric("Nº de Clusters (f2)", int(stats['f2']))

            st.subheader("Partição Encontrada")
            # Converte o dicionário para um DataFrame para melhor visualização
            df_clusters = pd.DataFrame(list(clusters.items()), columns=[
                                       'Nó', 'Representante do Cluster'])
            st.dataframe(df_clusters)
        else:
            st.warning(
                "O solver não encontrou uma solução viável dentro do limite de tempo.")
