# gui/app_desktop.py

import sys
import time
import glob
import os
import pandas as pd
import json
import numpy as np
import networkx as nx

# --- IMPORTS PARA IA ---
try:
    import openai
    import google.generativeai as genai
except ImportError:
    print("Aviso: Bibliotecas 'openai' ou 'google-generativeai' não instaladas.")

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QProgressBar, QFrame, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QComboBox, QSlider, QSpinBox, 
                             QGridLayout, QFileDialog, QRadioButton, QTabWidget, QGroupBox, 
                             QLineEdit, QTextEdit, QSplitter)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# --- IMPORTAÇÕES DO PROJETO ---

from src.core.instance_generator import generate_multigraph_instances
from src.public_management.graph_constructor import build_multigraph_from_csv
from src.public_management.optimization_model import solve_multigraph_cc
from experiments.public_management.run_heuristic import run_ga_experiment
from src.public_management.create_real_network import process_and_save_network
from src.public_management.genetic_algorithm import setup_genetic_algorithm
from deap import tools, algorithms

# ==============================================================================
# --- WORKER THREADS ---
# ==============================================================================

# --- WORKER: INTEGRAÇÃO COM LLM ---
class AIWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, provider, api_key, pareto_df, partitions_summary):
        super().__init__()
        self.provider = provider
        self.api_key = api_key
        self.pareto_df = pareto_df
        self.partitions_summary = partitions_summary

    def run(self):
        try:
            prompt = self._build_prompt()
            response_text = ""

            if self.provider == "OpenAI (GPT-4o/Turbo)":
                client = openai.OpenAI(api_key=self.api_key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Você é um cientista de dados especialista em detecção de fraudes em licitações."},
                        {"role": "user", "content": prompt}
                    ]
                )
                response_text = response.choices[0].message.content

            elif self.provider == "Google Gemini":
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                response_text = response.text

            self.finished.emit(response_text)

        except Exception as e:
            self.error.emit(f"Erro na API de IA: {str(e)}")

    def _build_prompt(self):
        # (Cálculo das estatísticas permanece igual)
        num_solutions = len(self.pareto_df)
        min_f1 = self.pareto_df['disagreement_f1'].min()
        max_f1 = self.pareto_df['disagreement_f1'].max()
        min_clusters = self.pareto_df['num_clusters_f2'].min()
        max_clusters = self.pareto_df['num_clusters_f2'].max()
        
        # Seleciona soluções específicas
        sol_min_k = self.pareto_df.iloc[0].to_dict()
        sol_max_k = self.pareto_df.iloc[-1].to_dict()
        
        # Calcula a variação percentual para dar contexto ao LLM
        delta_f1 = max_f1 - min_f1
        delta_k = max_clusters - min_clusters
        
        return f"""
        Aja como um Analista de Inteligência Sênior em combate à corrupção.
        Eu tenho os dados de uma execução de algoritmo de detecção de fraudes.
        
        DADOS OBTIDOS:
        - Soluções Encontradas: {num_solutions} (Granularidade da fronteira)
        - Variação de Desequilíbrio (Erro): {min_f1:.2f} até {max_f1:.2f} (Delta: {delta_f1:.2f})
        - Variação de Clusters: {min_clusters} até {max_clusters} (Delta: {delta_k})
        
        SOLUÇÕES EXTREMAS:
        - Cenário A (Mais Macro): {sol_min_k}
        - Cenário B (Mais Detalhado): {sol_max_k}

        DIRETRIZES RÍGIDAS:
        1. NÃO explique o que é Pareto, f1, f2 ou NSGA-II. Eu já sei isso.
        2. NÃO dê definições genéricas de "trade-off".
        3. Foque 100% na interpretação destes números específicos.

        RESPONDA:
        1. **Diagnóstico da Rede:** Olhando para o número de clusters (de {min_clusters} a {max_clusters}), a rede tende a ser um grande cartel centralizado ou vários micro-esquemas pulverizados? Justifique com os números.
        2. **Análise de Custo-Benefício:** Vale a pena aceitar o erro maior da solução {sol_min_k['solution_id']} para ter menos clusters para investigar? Ou a perda de precisão (aumento do f1) é muito drástica?
        3. **Ponto de Partida:** Qual solução específica (ID) você recomendaria para a equipe de auditoria começar amanhã de manhã e por quê?
        """

class ValidationWorker(QThread):
    status_update = Signal(str); finished = Signal(dict)
    def __init__(self, data_path, pop_size, ngen, cxpb, mutpb):
        super().__init__()
        self.data_path = data_path
        self.pop_size = pop_size
        self.ngen = ngen
        self.cxpb = cxpb
        self.mutpb = mutpb

    def run(self):
        try:
            self.status_update.emit("Iniciando Modelo Exato (Gurobi)...")
            G = build_multigraph_from_csv(self.data_path)
            if not G: 
                self.finished.emit({'error': 'Falha ao carregar o grafo.'})
                return
            
            lambda_values = [0.0, 0.25, 0.5, 0.75, 1.0]
            exact_results = []
            exact_start_time = time.time()
            
            for l in lambda_values:
                _, _, _, f1, f2 = solve_multigraph_cc(G, lambda_weight=l, time_limit=3600)
                if f1 is not None and f2 is not None:
                    exact_results.append({'num_clusters_f2': int(f2), 'disagreement_f1': f1})
            
            df_exact = pd.DataFrame(exact_results).drop_duplicates().sort_values(by='num_clusters_f2')
            exact_time = time.time() - exact_start_time

            self.status_update.emit("Iniciando Modelo Heurístico (AG)...")
            stats_h, df_heuristic, partitions = run_ga_experiment(
                self.data_path, "results_ui_validation", 
                self.pop_size, self.ngen, self.cxpb, self.mutpb
            )
            heuristic_time = stats_h['total_execution_time_minutes'] * 60
            
            self.finished.emit({
                'df_exact': df_exact.to_dict('records'),
                'time_exact': exact_time,
                'df_heuristic': df_heuristic.to_dict('records'),
                'time_heuristic': heuristic_time,
                'partitions': partitions
            })
        except Exception as e:
            self.finished.emit({'error': f'Ocorreu um erro: {e}'})

class RealDataWorker(QThread):
    progress = Signal(int, str); finished = Signal(dict)
    def __init__(self, data_path, pop_size, ngen, cxpb, mutpb):
        super().__init__()
        self.data_path = data_path
        self.pop_size = pop_size
        self.ngen = ngen
        self.cxpb = cxpb
        self.mutpb = mutpb

    def run(self):
        try:
            start_time = time.time()
            G = build_multigraph_from_csv(self.data_path)
            if not G: 
                self.finished.emit({'error': 'Falha ao carregar o grafo.'})
                return
            
            nodes = sorted(list(G.nodes()))
            toolbox = setup_genetic_algorithm(nodes, G)
            pop = toolbox.population(n=self.pop_size)
            hof = tools.ParetoFront()
            stats = tools.Statistics(lambda ind: ind.fitness.values)
            stats.register("min", np.min, axis=0)
            
            fitnesses = toolbox.map(toolbox.evaluate, pop)
            for ind, fit in zip(pop, fitnesses): ind.fitness.values = fit
            hof.update(pop)
            
            for gen in range(1, self.ngen + 1):
                offspring = toolbox.select(pop, len(pop))
                offspring = algorithms.varAnd(offspring, toolbox, self.cxpb, self.mutpb)
                invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
                fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
                for ind, fit in zip(invalid_ind, fitnesses): ind.fitness.values = fit
                hof.update(offspring)
                pop[:] = toolbox.select(pop + offspring, self.pop_size)
                
                record = stats.compile(pop)
                status_text = f"Geração {gen}/{self.ngen} | Min Desequilíbrio: {record['min'][0]:.2f}, Min Clusters: {record['min'][1]}"
                self.progress.emit(int((gen / self.ngen) * 100), status_text)
            
            total_time_minutes = (time.time() - start_time) / 60
            pareto_data, solution_partitions = [], {}
            int_to_node = {i: name for i, name in enumerate(nodes)}
            
            for i, ind in enumerate(hof):
                f1, f2 = ind.fitness.values
                sol_id = f"solution_{i}"
                pareto_data.append({'solution_id': sol_id, 'num_clusters_f2': int(f2), 'disagreement_f1': f1})
                solution_partitions[sol_id] = {int_to_node[n]: int_to_node[ind[n]] for n in range(len(ind))}
            
            df_pareto = pd.DataFrame(pareto_data).sort_values(by='num_clusters_f2').drop_duplicates()
            stats_data = {'total_time_minutes': round(total_time_minutes, 2), 'num_pareto_solutions': len(df_pareto)}
            self.finished.emit({'stats': stats_data, 'pareto_df': df_pareto.to_dict('records'), 'partitions': solution_partitions})
        except Exception as e:
            self.finished.emit({'error': f'Ocorreu um erro: {e}'})

class DataProcessingWorker(QThread):
    finished = Signal(str, str)
    def __init__(self, input_path, output_path): 
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
    def run(self):
        try: 
            rows = process_and_save_network(self.input_path, self.output_path)
            self.finished.emit(self.output_path, f"{rows} contratos processados. Rede pronta.")
        except Exception as e: 
            self.finished.emit("", f"Erro ao processar dados: {e}")

# --- WORKER ATUALIZADO PARA SUPORTAR RAW_VIZ ---
class VisualizationWorker(QThread):
    finished = Signal(object, object)
    def __init__(self, data_path, cluster_nodes=None, raw_viz=False, limit_nodes=None):
        super().__init__()
        self.data_path = data_path
        self.cluster_nodes = cluster_nodes
        self.raw_viz = raw_viz
        self.limit_nodes = limit_nodes

    def run(self):
        try:
            G_full = build_multigraph_from_csv(self.data_path)
            
            if self.raw_viz:
                # Garante que é um inteiro
                limit = int(self.limit_nodes)
                
                if len(G_full.nodes) > limit:
                    degrees = dict(G_full.degree())
                    # Pega os Top N nós por grau
                    top_nodes = sorted(degrees, key=degrees.get, reverse=True)[:limit]
                    H = G_full.subgraph(top_nodes)
                else: 
                    H = G_full
                k_val = 0.25 
            else:
                # Lógica para visualizar um cluster específico
                H = G_full.subgraph(self.cluster_nodes)
                k_val = None # Padrão

            pos = nx.spring_layout(H, seed=42, iterations=50, k=k_val)
            self.finished.emit(H, pos)
        except Exception as e:
            self.finished.emit(None, str(e))

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure(figsize=(5, 4), dpi=100)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)

# ==============================================================================
# --- JANELA PRINCIPAL ---
# ==============================================================================
# ==============================================================================
# --- JANELA PRINCIPAL ---
# ==============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard de Análise e Validação")
        self.setGeometry(100, 100, 1600, 900)
        self.current_pareto_df = None
        self.current_partitions = None
        self.real_data_path_processed = None
        self.current_analysis_file = None
        self.viz_data_raw = None     # guardar (Grafo, Posições, Título) da rede bruta
        self.viz_data_cluster = None # guardar (Grafo, Posições, Título) do cluster
        self._setup_ui()
        self.worker_thread = None
        self.populate_instances()
        # IMPORTANTE: Toggle mode chamado APENAS após a criação de todos os widgets
        self.toggle_mode()

    def _setup_ui(self):
        main_layout = QHBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # === PAINEL ESQUERDO (CONTROLES) ===
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.StyledPanel)
        control_frame.setFixedWidth(380)
        control_layout = QVBoxLayout(control_frame)
        
        # 1. Criar Tabs de Modo PRIMEIRO
        self.mode_tabs = QTabWidget()
        control_layout.addWidget(self.mode_tabs)
        
        # 2. Criar Conteúdo das Tabs
        # Tab Validação
        val_tab = QWidget(); val_lay = QVBoxLayout(val_tab)
        val_lay.addWidget(QLabel("Validação com dados sintéticos."))
        self.gen_btn = QPushButton("Gerar Instâncias"); self.gen_btn.clicked.connect(self.gen_inst); val_lay.addWidget(self.gen_btn)
        self.inst_combo = QComboBox(); val_lay.addWidget(QLabel("Instância:")); val_lay.addWidget(self.inst_combo); val_lay.addStretch()
        self.mode_tabs.addTab(val_tab, "Validação")

        # Tab Análise Real
        real_tab = QWidget(); real_lay = QVBoxLayout(real_tab)
        real_lay.addWidget(QLabel("1. Processamento:"))
        self.upl_btn = QPushButton("Carregar Dados"); self.upl_btn.clicked.connect(self.proc_real); real_lay.addWidget(self.upl_btn)
        self.file_lbl = QLabel("Nenhum arquivo."); self.file_lbl.setWordWrap(True); real_lay.addWidget(self.file_lbl)
        real_lay.addWidget(QFrame(frameShape=QFrame.HLine))
        real_lay.addWidget(QLabel("Pré-visualização (Nós):"))
        viz_lay = QHBoxLayout()
        self.viz_lim_spin = QSpinBox()
        self.viz_lim_spin.setMaximum(10000)  # <--- FORÇA O LIMITE MÁXIMO
        self.viz_lim_spin.setValue(10)
        self.viz_lim_spin.setSingleStep(1)
        self.viz_lim_spin.setSingleStep(10)
        # -----------------------------------
        viz_lay.addWidget(self.viz_lim_spin); self.btn_prev = QPushButton("👁️"); self.btn_prev.clicked.connect(self.prev_raw); viz_lay.addWidget(self.btn_prev)
        real_lay.addLayout(viz_lay); real_lay.addStretch()
        self.mode_tabs.addTab(real_tab, "Análise Real")
        
        # Tab Inspeção
        ins_tab = QWidget(); ins_lay = QVBoxLayout(ins_tab)
        ins_lay.addWidget(QLabel("Inspecione clusters."))
        ins_lay.addWidget(QLabel("Solução:")); self.viz_sol_combo = QComboBox(); self.viz_sol_combo.currentIndexChanged.connect(self.upd_clust_combo); ins_lay.addWidget(self.viz_sol_combo)
        ins_lay.addWidget(QLabel("Cluster:")); self.viz_clus_combo = QComboBox(); ins_lay.addWidget(self.viz_clus_combo)
        self.viz_btn = QPushButton("Visualizar"); self.viz_btn.setStyleSheet("background-color:#28a745;color:white;"); self.viz_btn.clicked.connect(self.viz_clus); ins_lay.addWidget(self.viz_btn)
        ins_lay.addStretch(); self.mode_tabs.addTab(ins_tab, "Inspeção")

        # Tab IA
        ia_tab = QWidget(); ia_lay = QVBoxLayout(ia_tab)
        ia_lay.addWidget(QLabel("Interpretação Automática"))
        ia_lay.addWidget(QLabel("Provedor:")); self.ia_provider = QComboBox(); self.ia_provider.addItems(["Google Gemini", "OpenAI (GPT-4o/Turbo)"]); ia_lay.addWidget(self.ia_provider)
        ia_lay.addWidget(QLabel("Chave API:")); self.ia_key = QLineEdit(); self.ia_key.setEchoMode(QLineEdit.Password); ia_lay.addWidget(self.ia_key)
        self.ia_btn = QPushButton("🤖 Gerar"); self.ia_btn.setStyleSheet("background-color:#6f42c1;color:white;"); self.ia_btn.clicked.connect(self.run_ia_analysis); ia_lay.addWidget(self.ia_btn)
        ia_lay.addStretch(); self.mode_tabs.addTab(ia_tab, "IA")

        # 3. Parâmetros AG
        self.ag_grp = QGroupBox("Parâmetros do AG"); p_lay = QGridLayout(self.ag_grp)
        p_lay.addWidget(QLabel("População:"),0,0); self.pop_sp = QSpinBox(); self.pop_sp.setRange(50,5000); self.pop_sp.setSingleStep(50); p_lay.addWidget(self.pop_sp,0,1)
        p_lay.addWidget(QLabel("Gerações:"),1,0); self.gen_sp = QSpinBox(); self.gen_sp.setRange(10,5000); self.gen_sp.setSingleStep(10); p_lay.addWidget(self.gen_sp,1,1)
        p_lay.addWidget(QLabel("Crossover (%):"),2,0); self.cx_sl = QSlider(Qt.Horizontal); self.cx_sl.setRange(0,100); self.cx_lbl=QLabel(); self.cx_sl.valueChanged.connect(lambda v:self.cx_lbl.setText(f"{v}%")); p_lay.addWidget(self.cx_sl,2,1); p_lay.addWidget(self.cx_lbl,2,2)
        p_lay.addWidget(QLabel("Mutação (%):"),3,0); self.mt_sl = QSlider(Qt.Horizontal); self.mt_sl.setRange(0,100); self.mt_lbl=QLabel(); self.mt_sl.valueChanged.connect(lambda v:self.mt_lbl.setText(f"{v}%")); p_lay.addWidget(self.mt_sl,3,1); p_lay.addWidget(self.mt_lbl,3,2)
        control_layout.addWidget(self.ag_grp); control_layout.addStretch()
        
        # 4. Botão Executar (CRIADO AGORA, ANTES DE CONECTAR SINAIS DE TAB)
        self.run_btn = QPushButton("Executar"); self.run_btn.setStyleSheet("background-color:#007bff;color:white;padding:10px;"); self.run_btn.clicked.connect(self.start_analysis); control_layout.addWidget(self.run_btn)

        # 5. Conecta sinal de troca de aba (AGORA É SEGURO)
        self.mode_tabs.currentChanged.connect(self.toggle_mode)

        # === PAINEL DIREITO (RESULTADOS) ===
        self.res_tabs = QTabWidget()
        
        # Aba Resultados
        g_tab = QWidget(); g_lay = QVBoxLayout(g_tab)
        self.cv = MplCanvas(self); self.tb = NavigationToolbar(self.cv, self); g_lay.addWidget(self.tb); g_lay.addWidget(self.cv)
        self.st_area = QWidget(); st_lay = QHBoxLayout(self.st_area); self.t1_lbl = QLabel("T. Exato: --"); self.t2_lbl = QLabel("T. Heurística: --"); st_lay.addWidget(self.t1_lbl); st_lay.addWidget(self.t2_lbl); g_lay.addWidget(self.st_area)
        tb_area = QWidget(); tb_lay = QHBoxLayout(tb_area); self.tbl1 = QTableWidget(); self.tbl2 = QTableWidget(); tb_lay.addWidget(self.tbl1); tb_lay.addWidget(self.tbl2); g_lay.addWidget(tb_area)
        dn_lay = QHBoxLayout(); self.dn_csv = QPushButton("📥 CSV"); self.dn_csv.clicked.connect(self.save_csv); self.dn_json = QPushButton("📥 JSON"); self.dn_json.clicked.connect(self.save_json); dn_lay.addWidget(self.dn_csv); dn_lay.addWidget(self.dn_json); g_lay.addLayout(dn_lay)
        self.res_tabs.addTab(g_tab, "📈 Resultados")

        # Aba Visualização Rede
        v_tab = QWidget(); v_lay = QVBoxLayout(v_tab)
        v_ctl_lay = QHBoxLayout()
        v_ctl_lay.addWidget(QLabel("Modo de Visualização:"))
        self.viz_mode_combo = QComboBox()
        self.viz_mode_combo.addItem("Nenhuma Visualização Disponível")
        self.viz_mode_combo.currentIndexChanged.connect(self.switch_visualization_view)
        v_ctl_lay.addWidget(self.viz_mode_combo)
        v_ctl_lay.addStretch()
        v_lay.addLayout(v_ctl_lay)
        self.v_cv = MplCanvas(self); self.v_tb = NavigationToolbar(self.v_cv, self); v_lay.addWidget(self.v_tb); v_lay.addWidget(self.v_cv)
        self.res_tabs.addTab(v_tab, "🕸️ Visualização")

        # Aba Texto IA
        ia_res_tab = QWidget(); ia_res_lay = QVBoxLayout(ia_res_tab)
        self.ia_text = QTextEdit(); self.ia_text.setReadOnly(True); self.ia_text.setPlaceholderText("A interpretação da IA aparecerá aqui...")
        ia_res_lay.addWidget(self.ia_text)
        self.res_tabs.addTab(ia_res_tab, "🤖 Relatório IA")

        r_lay = QVBoxLayout(); r_lay.addWidget(self.res_tabs)
        self.st_lbl = QLabel("Pronto."); self.p_bar = QProgressBar(); r_lay.addWidget(self.st_lbl); r_lay.addWidget(self.p_bar)
        main_layout.addWidget(control_frame); main_layout.addLayout(r_lay)

    # --- LÓGICA IA ---
    def run_ia_analysis(self):
        k=self.ia_key.text()
        if not k: self.st_lbl.setText("Erro: API Key."); return
        if self.current_pareto_df is None: self.st_lbl.setText("Erro: Sem dados."); return
        self.ia_btn.setEnabled(False); self.st_lbl.setText("Enviando...")
        self.iaw=AIWorker(self.ia_provider.currentText(),k,self.current_pareto_df,None)
        self.iaw.finished.connect(self.on_ia_fin); self.iaw.error.connect(self.on_ia_err); self.iaw.start()

    def on_ia_fin(self, t): self.ia_btn.setEnabled(True); self.st_lbl.setText("OK"); self.res_tabs.setCurrentIndex(2); self.ia_text.setMarkdown(t)
    def on_ia_err(self, e): self.ia_btn.setEnabled(True); self.st_lbl.setText(e)

    # --- LÓGICA DE UI E EXECUÇÃO ---
    def toggle_mode(self):
        i = self.mode_tabs.currentIndex()
        if i==0: 
            self.run_btn.show(); self.run_btn.setText("Validar"); self.pop_sp.setValue(200); self.gen_sp.setValue(100); self.cx_sl.setValue(70); self.mt_sl.setValue(20)
            self.run_btn.setEnabled(True); self.dn_json.hide()
        elif i==1: 
            self.run_btn.show(); self.run_btn.setText("Executar"); self.pop_sp.setValue(2000); self.gen_sp.setValue(1000); self.cx_sl.setValue(50); self.mt_sl.setValue(50)
            self.run_btn.setEnabled(self.real_data_path_processed is not None); self.dn_json.show()
        else: self.run_btn.hide(); self.update_sol_combo()

    def upd_clust_combo(self):
        self.viz_clus_combo.clear(); sid = self.viz_sol_combo.currentText()
        if not self.current_partitions or not sid or "Nenhum" in sid: 
            if self.current_partitions: self.viz_sol_combo.addItems(list(self.current_partitions.keys()))
            else: self.viz_sol_combo.addItem("Nenhum resultado")
            return
        part = self.current_partitions[sid]; clus = {}
        for n, c in part.items(): clus.setdefault(c, []).append(n)
        sc = sorted(clus.items(), key=lambda x: len(x[1]), reverse=True)
        for c, ns in sc: self.viz_clus_combo.addItem(f"Cluster {c} ({len(ns)} nós)", userData=ns)

    def update_sol_combo(self): 
        self.viz_sol_combo.clear()
        if self.current_partitions: self.viz_sol_combo.addItems(list(self.current_partitions.keys())); self.viz_sol_combo.setCurrentIndex(0); self.upd_clust_combo()
        else: self.viz_sol_combo.addItem("Nenhum resultado")

    def update_viz_mode_combo(self):
        self.viz_mode_combo.blockSignals(True) # Evita loops
        self.viz_mode_combo.clear()
        
        options = []
        if self.viz_data_raw: options.append("Rede Bruta (Pré-visualização)")
        if self.viz_data_cluster: options.append("Cluster Otimizado (Seleção)")
        
        if not options: self.viz_mode_combo.addItem("Nenhuma Visualização Disponível")
        else: self.viz_mode_combo.addItems(options)
        
        # Seleciona automaticamente o último gerado (o mais recente)
        if options: self.viz_mode_combo.setCurrentIndex(len(options)-1)
        
        self.viz_mode_combo.blockSignals(False)
        self.switch_visualization_view() # Força a atualização do gráfico

    def switch_visualization_view(self):
        txt = self.viz_mode_combo.currentText()
        target_data = None
        
        if "Rede Bruta" in txt: target_data = self.viz_data_raw
        elif "Cluster Otimizado" in txt: target_data = self.viz_data_cluster
            
        self.v_cv.axes.clear()
        if target_data:
            H, pos, title = target_data
            self.plot_g(H, pos, self.v_cv, title)
        self.v_cv.draw()

    def prev_raw(self):
        if not self.real_data_path_processed: self.st_lbl.setText("Sem arquivo."); return
        l = self.viz_lim_spin.value(); self.st_lbl.setText(f"Gerando pré-visualização..."); self.btn_prev.setEnabled(False)
        self.vw = VisualizationWorker(self.real_data_path_processed, raw_viz=True, limit_nodes=l)
        self.vw.finished.connect(self.on_raw_fin); self.vw.start()

    def on_raw_fin(self, H, pos):
        self.btn_prev.setEnabled(True)
        if not H: self.st_lbl.setText(f"Erro: {pos}"); return
        self.st_lbl.setText("Pré-visualização gerada.")
        
        # Salva os dados em vez de plotar direto
        self.viz_data_raw = (H, pos, f"Rede (Top {len(H.nodes)} Hubs)")
        self.res_tabs.setCurrentIndex(1) # Vai para a aba
        self.update_viz_mode_combo() # Atualiza o menu e plota

    def viz_clus(self):
        ns = self.viz_clus_combo.currentData()
        if not ns: return
        self.viz_btn.setEnabled(False); self.st_lbl.setText("Gerando...")
        self.vw = VisualizationWorker(self.current_analysis_file, ns)
        self.vw.finished.connect(self.on_clus_fin); self.vw.start()

    def on_clus_fin(self, H, pos):
        self.viz_btn.setEnabled(True)
        if not H: self.st_lbl.setText(f"Erro: {pos}"); return
        self.st_lbl.setText("Pronto.")
        r = [d.get('positive_prob',0) for u,v,d in H.edges(data=True)]; ar=np.mean(r) if r else 0
        
        # Salva os dados
        self.viz_data_cluster = (H, pos, f"Cluster ({len(H.nodes)} nós) | Risco: {ar:.2f}")
        self.res_tabs.setCurrentIndex(1) # Vai para a aba
        self.update_viz_mode_combo() # Atualiza o menu e plota

    def plot_g(self, H, pos, cv, tit):
        cv.axes.clear(); Gv=nx.Graph(); ew={}; er={}
        for u,v,d in H.edges(data=True): k=tuple(sorted((u,v))); ew[k]=ew.get(k,0)+1; er[k]=er.get(k,0.0)+d.get('positive_prob',0.5)
        for (u,v),c in ew.items(): Gv.add_edge(u,v,weight=c,risk=er[(u,v)]/c)
        Gv.add_nodes_from(H.nodes()); nn=len(Gv.nodes()); d=dict(Gv.degree)
        ns=[v*(3000/(nn**0.6) if nn>0 else 300) for v in d.values()] if d else 300
        ec=['green' if da['risk']<0.4 else '#FFC107' if da['risk']<0.7 else 'red' for u,v,da in Gv.edges(data=True)]
        width=[1+np.log(da['weight'])*2 for u,v,da in Gv.edges(data=True)]
        nx.draw_networkx_nodes(Gv,pos,ax=cv.axes,node_size=ns,node_color='#3366cc',alpha=0.8)
        nx.draw_networkx_edges(Gv,pos,ax=cv.axes,edge_color=ec,width=width,alpha=0.6)
        if nn<50: nx.draw_networkx_labels(Gv,pos,ax=cv.axes,font_size=10)
        else: 
            tn=sorted(d,key=d.get,reverse=True)[:5]; lb={n:n for n in tn}
            nx.draw_networkx_labels(Gv,pos,labels=lb,ax=cv.axes,font_size=10,font_weight='bold')
        cv.axes.set_title(tit); cv.axes.axis('off'); cv.draw()

    def proc_real(self):
        p,_=QFileDialog.getOpenFileName(self,"Abrir CSV","","CSV (*.csv)"); 
        if not p: return
        self.st_lbl.setText("Processando..."); self.run_btn.setEnabled(False)
        self.dpw=DataProcessingWorker(p,"data/rede_real_input_ui.csv"); self.dpw.finished.connect(self.on_dp_fin); self.dpw.start()

    def on_dp_fin(self, p, m):
        self.st_lbl.setText(m); self.real_data_path_processed=p
        if p: self.file_lbl.setText(f"Pronto: {os.path.basename(p)}"); self.run_btn.setEnabled(True)

    def start_analysis(self):
        self.run_btn.setEnabled(False); self.st_lbl.setText("Executando..."); self.p_bar.setValue(0)
        p,n,c,m = self.pop_sp.value(), self.gen_sp.value(), self.cx_sl.value()/100, self.mt_sl.value()/100
        self.res_tabs.setCurrentIndex(0)
        if self.mode_tabs.currentIndex()==0:
            pth=self.inst_combo.currentText()
            if not pth or "Nenhuma" in pth: self.st_lbl.setText("Erro: Selecione instância."); return
            self.current_analysis_file=pth; self.p_bar.setRange(0,0)
            self.wt=ValidationWorker(pth,p,n,c,m); self.wt.status_update.connect(lambda t: self.st_lbl.setText(t))
        else:
            if not self.real_data_path_processed: self.st_lbl.setText("Erro: Processe dados."); return
            self.current_analysis_file=self.real_data_path_processed
            self.wt=RealDataWorker(self.real_data_path_processed,p,n,c,m); self.wt.progress.connect(lambda v,t: (self.p_bar.setValue(v), self.st_lbl.setText(t)))
        self.wt.finished.connect(self.disp_res); self.wt.start()

    def disp_res(self, res):
        self.run_btn.setEnabled(True); self.p_bar.setRange(0,100); self.p_bar.setValue(100)
        if 'error' in res: self.st_lbl.setText(res['error']); return
        self.cv.axes.clear()
        if self.mode_tabs.currentIndex()==0:
            self.run_btn.setText("Validar"); self.st_lbl.setText("Validação OK")
            self.t1_lbl.setText(f"Exato: {res['time_exact']:.2f}s"); self.t1_lbl.show()
            self.t2_lbl.setText(f"Heurística: {res['time_heuristic']:.2f}s")
            de=pd.DataFrame(res['df_exact']); dh=pd.DataFrame(res['df_heuristic'])
            self._pt(self.tbl1,de,"Exato"); self._pt(self.tbl2,dh,"AG")
            self.current_pareto_df=pd.concat([de.assign(F='Exato'),dh.assign(F='AG')]); self.current_partitions=res.get('partitions')
            if not de.empty: self.cv.axes.plot(de['num_clusters_f2'],de['disagreement_f1'],marker='*',ls='--',label='Exato',color='blue')
            if not dh.empty: self.cv.axes.scatter(dh['num_clusters_f2'],dh['disagreement_f1'],marker='o',label='AG',color='orange')
        else:
            self.run_btn.setText("Executar"); self.st_lbl.setText("Concluído")
            self.t1_lbl.hide(); self.t2_lbl.setText(f"Tempo: {res['stats']['total_time_minutes']:.2f} min")
            dp=pd.DataFrame(res['pareto_df']); self._pt(self.tbl1,dp,"Pareto"); self.tbl2.hide()
            self.current_pareto_df=dp; self.current_partitions=res['partitions']
            if not dp.empty: self.cv.axes.scatter(dp['num_clusters_f2'],dp['disagreement_f1'],marker='o',label='AG',color='green')
        
        self.cv.axes.legend(); self.cv.draw(); self.dn_csv.setEnabled(True); self.dn_json.setEnabled(bool(self.current_partitions))
        if self.current_partitions: self.update_sol_combo()

    def _pt(self, tb, df, t):
        tb.clear(); tb.show(); tb.setRowCount(len(df)+1); tb.setColumnCount(len(df.columns))
        tb.setItem(0,0,QTableWidgetItem(t)); tb.setHorizontalHeaderLabels(df.columns)
        for i,r in df.iterrows(): 
            for j,v in enumerate(r): tb.setItem(i+1,j,QTableWidgetItem(str(v)))

    def save_csv(self): 
        if self.current_pareto_df is not None: 
            p,_=QFileDialog.getSaveFileName(self,"Salvar","res.csv","CSV (*.csv)"); 
            if p: self.current_pareto_df.to_csv(p,index=False)
    def save_json(self): 
        if self.current_partitions: 
            p,_=QFileDialog.getSaveFileName(self,"Salvar","part.json","JSON (*.json)"); 
            if p: 
                with open(p,'w') as f: json.dump(self.current_partitions,f)
    def populate_instances(self):
        self.inst_combo.clear(); fs=glob.glob("data/run1_*.csv"); 
        if fs: self.inst_combo.addItems(fs)
    def gen_inst(self): 
        self.st_lbl.setText("Gerando..."); QApplication.processEvents(); generate_multigraph_instances(); self.populate_instances(); self.st_lbl.setText("OK")

if __name__ == "__main__":
    app = QApplication(sys.argv); w = MainWindow(); w.show(); sys.exit(app.exec())