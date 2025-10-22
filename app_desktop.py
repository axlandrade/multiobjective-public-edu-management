# app.py

import sys
import time
import glob
import os
import pandas as pd
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QProgressBar, QFrame, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QComboBox, QSlider, QSpinBox, 
                             QGridLayout, QFileDialog, QRadioButton, QTabWidget, QGroupBox)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# --- IMPORTAÇÕES DO PROJETO ---
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.instance_generator import generate_multigraph_instances
from src.graph_constructor import build_multigraph_from_csv
from src.optimization_model import solve_multigraph_cc
from experiments.heuristic.run_genetic_algorithm import run_ga_experiment
from src.create_real_network import process_and_save_network

# --- CORREÇÃO: ADICIONANDO IMPORTS FALTANTES ---
from src.genetic_algorithm import setup_genetic_algorithm
from deap import tools, algorithms
import numpy as np
# --- FIM DA CORREÇÃO ---


# --- WORKER THREADS (Validação, Análise Real, e Processamento de Dados) ---
class ValidationWorker(QThread):
    status_update = Signal(str); finished = Signal(dict)
    def __init__(self, data_path, pop_size, ngen, cxpb, mutpb):
        super().__init__(); self.data_path, self.pop_size, self.ngen, self.cxpb, self.mutpb = data_path, pop_size, ngen, cxpb, mutpb
    def run(self):
        try:
            self.status_update.emit("Iniciando Modelo Exato (Gurobi)...")
            G = build_multigraph_from_csv(self.data_path)
            if not G: self.finished.emit({'error': 'Falha ao carregar o grafo.'}); return
            
            lambda_values = [0.0, 0.25, 0.5, 0.75, 1.0]
            exact_results = []
            exact_start_time = time.time()
            for l in lambda_values:
                _, _, _, f1, f2 = solve_multigraph_cc(G, lambda_weight=l, time_limit=3600)
                if f1 is not None and f2 is not None: exact_results.append({'num_clusters_f2': int(f2), 'disagreement_f1': f1})
            
            df_exact = pd.DataFrame(exact_results).drop_duplicates().sort_values(by='num_clusters_f2')
            exact_time = time.time() - exact_start_time

            self.status_update.emit("Iniciando Modelo Heurístico (AG)...")
            stats_h, df_heuristic, _ = run_ga_experiment(self.data_path, "results_ui_validation", self.pop_size, self.ngen, self.cxpb, self.mutpb)
            heuristic_time = stats_h['total_execution_time_minutes'] * 60
            self.finished.emit({'df_exact': df_exact.to_dict('records'), 'time_exact': exact_time, 'df_heuristic': df_heuristic.to_dict('records'), 'time_heuristic': heuristic_time})
        except Exception as e: self.finished.emit({'error': f'Ocorreu um erro: {e}'})

class RealDataWorker(QThread):
    progress = Signal(int, str); finished = Signal(dict)
    def __init__(self, data_path, pop_size, ngen, cxpb, mutpb):
        super().__init__(); self.data_path, self.pop_size, self.ngen, self.cxpb, self.mutpb = data_path, pop_size, ngen, cxpb, mutpb
    def run(self):
        try:
            start_time = time.time()
            G = build_multigraph_from_csv(self.data_path)
            if not G: self.finished.emit({'error': 'Falha ao carregar o grafo.'}); return
            
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
        except Exception as e: self.finished.emit({'error': f'Ocorreu um erro: {e}'})

class DataProcessingWorker(QThread):
    finished = Signal(str, str)
    def __init__(self, input_path, output_path):
        super().__init__(); self.input_path, self.output_path = input_path, output_path
    def run(self):
        try:
            rows = process_and_save_network(self.input_path, self.output_path)
            self.finished.emit(self.output_path, f"{rows} contratos processados. Rede pronta para análise.")
        except Exception as e:
            self.finished.emit("", f"Erro ao processar dados: {e}")

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure(figsize=(5, 4), dpi=100)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard de Análise e Validação de Redes de Corrupção")
        self.setGeometry(100, 100, 1600, 900)
        self.current_pareto_df = None
        self.current_partitions = None
        self.real_data_path_processed = None
        self._setup_ui()
        self.worker_thread = None
        self.populate_instances()
        self.toggle_mode()

    def _setup_ui(self):
        main_layout = QHBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.StyledPanel)
        control_frame.setFixedWidth(380)
        control_layout = QVBoxLayout(control_frame)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.toggle_mode)
        control_layout.addWidget(self.tab_widget)
        
        # Aba de Validação
        validation_tab = QWidget()
        validation_layout = QVBoxLayout(validation_tab)
        validation_layout.addWidget(QLabel("Gere e selecione uma instância sintética para validar a heurística."))
        self.generate_button = QPushButton("Gerar/Atualizar Instâncias")
        self.generate_button.clicked.connect(self.generate_instances)
        self.instance_combo = QComboBox()
        validation_layout.addWidget(self.generate_button)
        validation_layout.addWidget(QLabel("Selecione a instância:"))
        validation_layout.addWidget(self.instance_combo)
        validation_layout.addStretch()
        self.tab_widget.addTab(validation_tab, "Validação (Sintético)")

        # Aba de Análise Real
        real_data_tab = QWidget()
        real_data_layout = QVBoxLayout(real_data_tab)
        real_data_layout.addWidget(QLabel("1. Processe os dados brutos para criar a rede."))
        self.upload_button = QPushButton("Carregar e Processar Dados Brutos")
        self.upload_button.clicked.connect(self.process_real_data)
        self.file_label = QLabel("Nenhum arquivo processado.")
        self.file_label.setWordWrap(True)
        real_data_layout.addWidget(self.upload_button)
        real_data_layout.addWidget(self.file_label)
        real_data_layout.addWidget(QFrame(frameShape=QFrame.HLine))
        real_data_layout.addWidget(QLabel("2. Ajuste os parâmetros e execute a análise."))
        real_data_layout.addStretch()
        self.tab_widget.addTab(real_data_tab, "Análise (Dados Reais)")
        
        # Parâmetros Comuns do AG
        self.ag_params_group = QGroupBox("Parâmetros do Algoritmo Genético")
        params_layout = QGridLayout(self.ag_params_group)
        params_layout.addWidget(QLabel("Tamanho da População:"), 0, 0)
        self.pop_spinbox = QSpinBox()
        self.pop_spinbox.setRange(50, 5000)
        self.pop_spinbox.setSingleStep(50)
        params_layout.addWidget(self.pop_spinbox, 0, 1)
        params_layout.addWidget(QLabel("Número de Gerações:"), 1, 0)
        self.ngen_spinbox = QSpinBox()
        self.ngen_spinbox.setRange(10, 5000)
        self.ngen_spinbox.setSingleStep(10)
        params_layout.addWidget(self.ngen_spinbox, 1, 1)
        params_layout.addWidget(QLabel("Prob. Crossover (%):"), 2, 0)
        self.cxpb_slider = QSlider(Qt.Horizontal)
        self.cxpb_slider.setRange(0, 100)
        self.cxpb_label = QLabel()
        self.cxpb_slider.valueChanged.connect(lambda v: self.cxpb_label.setText(f"{v}%"))
        params_layout.addWidget(self.cxpb_slider, 2, 1)
        params_layout.addWidget(self.cxpb_label, 2, 2)
        params_layout.addWidget(QLabel("Prob. Mutação (%):"), 3, 0)
        self.mutpb_slider = QSlider(Qt.Horizontal)
        self.mutpb_slider.setRange(0, 100)
        self.mutpb_label = QLabel()
        self.mutpb_slider.valueChanged.connect(lambda v: self.mutpb_label.setText(f"{v}%"))
        params_layout.addWidget(self.mutpb_slider, 3, 1)
        params_layout.addWidget(self.mutpb_label, 3, 2)
        control_layout.addWidget(self.ag_params_group)

        control_layout.addStretch()
        self.run_button = QPushButton("Executar")
        self.run_button.setStyleSheet("background-color:#007bff;color:white;padding:10px;")
        self.run_button.clicked.connect(self.start_analysis)
        control_layout.addWidget(self.run_button)
        self.toggle_mode()

        # Painel de Resultados (Direita)
        results_layout = QVBoxLayout()
        self.canvas = MplCanvas(self)
        self.toolbar = NavigationToolbar(self.canvas, self)
        results_layout.addWidget(self.toolbar)
        results_layout.addWidget(self.canvas)
        self.stats_area = QWidget()
        stats_layout = QHBoxLayout(self.stats_area)
        self.time_label_1 = QLabel("Tempo Exato: -- s")
        self.time_label_2 = QLabel("Tempo Heurística: -- s")
        stats_layout.addWidget(self.time_label_1)
        stats_layout.addWidget(self.time_label_2)
        results_layout.addWidget(self.stats_area)
        tables_area = QWidget()
        tables_layout = QHBoxLayout(tables_area)
        self.table1 = QTableWidget()
        self.table2 = QTableWidget()
        tables_layout.addWidget(self.table1)
        tables_layout.addWidget(self.table2)
        results_layout.addWidget(tables_area)
        self.download_button_csv = QPushButton("📥 Download Fronteira (.csv)")
        self.download_button_csv.clicked.connect(self.save_csv)
        self.download_button_json = QPushButton("📥 Download Partições (.json)")
        self.download_button_json.clicked.connect(self.save_json)
        downloads_layout = QHBoxLayout()
        downloads_layout.addWidget(self.download_button_csv)
        downloads_layout.addWidget(self.download_button_json)
        results_layout.addLayout(downloads_layout)
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Pronto.")
        self.progress_bar = QProgressBar()
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        results_layout.addLayout(status_layout)
        
        main_layout.addWidget(control_frame)
        main_layout.addLayout(results_layout)

    def toggle_mode(self):
        is_validation = self.tab_widget.currentIndex() == 0
        self.run_button.setText("Executar Validação" if is_validation else "Executar Análise de Dados Reais")
        if is_validation:
            self.pop_spinbox.setValue(200); self.ngen_spinbox.setValue(100); self.cxpb_slider.setValue(70); self.mutpb_slider.setValue(20)
        else:
            self.pop_spinbox.setValue(2000); self.ngen_spinbox.setValue(1000); self.cxpb_slider.setValue(50); self.mutpb_slider.setValue(50)
        self.run_button.setEnabled(is_validation or (self.real_data_path_processed is not None))

    def process_real_data(self):
        input_path, _ = QFileDialog.getOpenFileName(self, "Abrir Arquivo de Dados Brutos", "", "CSV Files (*.csv)")
        if not input_path: return
        self.status_label.setText("Processando dados brutos..."); self.run_button.setEnabled(False)
        output_path = "data/rede_real_input_ui.csv"
        self.worker_thread = DataProcessingWorker(input_path, output_path)
        self.worker_thread.finished.connect(self.on_data_processed)
        self.worker_thread.start()

    def on_data_processed(self, output_path, message):
        self.status_label.setText(message)
        if output_path:
            self.real_data_path_processed = output_path
            self.file_label.setText(f"Pronto: {os.path.basename(output_path)}")
            self.run_button.setEnabled(True)

    def start_analysis(self):
        self.run_button.setEnabled(False); self.run_button.setText("Executando...")
        self.progress_bar.setValue(0)
        pop, ngen, cxpb, mutpb = self.pop_spinbox.value(), self.ngen_spinbox.value(), self.cxpb_slider.value()/100.0, self.mutpb_slider.value()/100.0
        
        if self.tab_widget.currentIndex() == 0:
            path = self.instance_combo.currentText()
            if not path or "Nenhuma" in path: self.status_label.setText("Erro: Nenhuma instância selecionada."); return
            self.progress_bar.setRange(0, 0)
            self.worker_thread = ValidationWorker(path, pop, ngen, cxpb, mutpb)
            self.worker_thread.status_update.connect(self.update_status)
        else:
            if not self.real_data_path_processed: self.status_label.setText("Erro: Nenhum arquivo de dados processado."); return
            self.worker_thread = RealDataWorker(self.real_data_path_processed, pop, ngen, cxpb, mutpb)
            self.worker_thread.progress.connect(self.update_progress)
        
        self.worker_thread.finished.connect(self.display_results)
        self.worker_thread.start()
    
    def display_results(self, results):
        self.run_button.setEnabled(True); self.progress_bar.setRange(0, 100); self.progress_bar.setValue(100)
        if 'error' in results: self.status_label.setText(f"Erro: {results['error']}"); return
        
        self.canvas.axes.clear()
        
        if self.tab_widget.currentIndex() == 0:
            self.run_button.setText("Executar Validação"); self.status_label.setText("Validação Concluída!")
            self.time_label_1.setText(f"Tempo Exato: {results['time_exact']:.2f} s"); self.time_label_1.show()
            self.time_label_2.setText(f"Tempo Heurística: {results['time_heuristic']:.2f} s")
            df_e = pd.DataFrame(results['df_exact']); self._populate_table(self.table1, df_e, "Ótima (Exato)")
            df_h = pd.DataFrame(results['df_heuristic']); self._populate_table(self.table2, df_h, "Aproximada (AG)")
            self.current_pareto_df = pd.concat([df_e, df_h]); self.current_partitions = None
            if not df_e.empty: self.canvas.axes.plot(df_e['num_clusters_f2'], df_e['disagreement_f1'], marker='*', ls='--', label='Ótima (Exato)', color='blue')
            if not df_h.empty: self.canvas.axes.scatter(df_h['num_clusters_f2'], df_h['disagreement_f1'], marker='o', label='Aproximada (AG)', s=100, color='orange')
            self.canvas.axes.set_title("Comparativo de Fronteiras de Pareto"); self.download_button_json.hide()
        else:
            self.run_button.setText("Executar Análise"); self.status_label.setText("Análise Concluída!")
            stats = results['stats']
            self.time_label_1.hide()
            self.time_label_2.setText(f"Tempo Total: {stats['total_time_minutes']:.2f} min | Soluções: {stats['num_pareto_solutions']}")
            df_p = pd.DataFrame(results['pareto_df']); self._populate_table(self.table1, df_p, "Fronteira de Pareto")
            self.table2.hide()
            self.current_pareto_df = df_p; self.current_partitions = results['partitions']
            if not df_p.empty: self.canvas.axes.scatter(df_p['num_clusters_f2'], df_p['disagreement_f1'], marker='o', label='Fronteira (AG)')
            self.canvas.axes.set_title("Fronteira de Pareto (Dados Reais)"); self.download_button_json.show()
        
        self.canvas.axes.set_xlabel("Nº Clusters (f2)"); self.canvas.axes.set_ylabel("Desequilíbrio (f1)")
        self.canvas.axes.grid(True); self.canvas.axes.legend(); self.canvas.draw()
        self.download_button_csv.setEnabled(True)
        if self.current_partitions: self.download_button_json.setEnabled(True)
    
    def save_csv(self):
        if self.current_pareto_df is not None:
            path, _ = QFileDialog.getSaveFileName(self, "Salvar CSV", "results.csv", "CSV Files (*.csv)")
            if path: self.current_pareto_df.to_csv(path, index=False)
    
    def save_json(self):
        if self.current_partitions is not None:
            path, _ = QFileDialog.getSaveFileName(self, "Salvar Partições JSON", "partitions.json", "JSON Files (*.json)")
            if path:
                with open(path, 'w') as f: json.dump(self.current_partitions, f, indent=4)
    
    def populate_instances(self):
        self.instance_combo.clear()
        files = sorted(glob.glob("data/run1_*.csv"))
        if files: self.instance_combo.addItems(files)
        else: self.instance_combo.addItem("Nenhuma instância encontrada")
    
    def generate_instances(self):
        self.status_label.setText("Gerando..."); QApplication.processEvents()
        generate_multigraph_instances()
        self.status_label.setText("Instâncias geradas."); self.populate_instances()

    def update_progress(self, v, t):
        self.progress_bar.setValue(v); self.status_label.setText(t)
    
    def update_status(self, t):
        self.status_label.setText(t)

    def _populate_table(self, table, df, title):
        table.clear(); table.show(); table.setRowCount(0); table.setColumnCount(0)
        if df.empty: return
        
        table.setRowCount(len(df) + 1); table.setColumnCount(len(df.columns))
        t_item = QTableWidgetItem(title); font = QFont(); font.setBold(True)
        t_item.setFont(font); table.setItem(0, 0, t_item); table.setSpan(0, 0, 1, len(df.columns))
        table.setHorizontalHeaderLabels(df.columns)
        
        for i, row in df.iterrows():
            for j, val in enumerate(row): table.setItem(i + 1, j, QTableWidgetItem(f"{val:.4f}" if isinstance(val, float) else str(val)))
        
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())