# app_desktop.py

import sys
import time
import glob
import os
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QProgressBar, QFrame, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QComboBox, QSlider, QSpinBox, QGridLayout) # QGridLayout adicionado
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# --- IMPORTAÇÕES DO SEU PROJETO ---
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.instance_generator import generate_multigraph_instances
from src.graph_constructor import build_multigraph_from_csv
from src.optimization_model import solve_multigraph_cc
from experiments.heuristic.run_genetic_algorithm import run_ga_experiment

# --- WORKER THREAD (sem alterações) ---
class ValidationWorker(QThread):
    status_update = Signal(str)
    finished = Signal(dict)

    def __init__(self, data_path, pop_size, ngen, cxpb, mutpb):
        super().__init__()
        self.data_path = data_path
        self.pop_size = pop_size
        self.ngen = ngen
        self.cxpb = cxpb
        self.mutpb = mutpb

    def run(self):
        try:
            # (Lógica do modelo exato sem alterações)
            self.status_update.emit("Iniciando Modelo Exato (Gurobi)...")
            exact_start_time = time.time()
            G = build_multigraph_from_csv(self.data_path)
            if not G: 
                self.finished.emit({'error': 'Falha ao carregar o grafo.'})
                return
            lambda_values = [0.0, 0.25, 0.5, 0.75, 1.0]
            exact_results = []
            for l in lambda_values:
                _, _, _, f1, f2 = solve_multigraph_cc(G, lambda_weight=l, time_limit=3600)
                if f1 is not None and f2 is not None:
                    exact_results.append({'num_clusters_f2': int(f2), 'disagreement_f1': f1})
            df_exact = pd.DataFrame(exact_results).drop_duplicates().sort_values(by='num_clusters_f2')
            exact_time = time.time() - exact_start_time

            self.status_update.emit("Modelo Exato concluído. Iniciando Modelo Heurístico (AG)...")
            stats_h, df_heuristic, _ = run_ga_experiment(
                data_path=self.data_path, output_dir="results_ui_validation",
                pop_size=self.pop_size, ngen=self.ngen, 
                cxpb=self.cxpb, mutpb=self.mutpb
            )
            heuristic_time = stats_h['total_execution_time_minutes'] * 60

            final_results = {
                'df_exact': df_exact.to_dict('records'),
                'time_exact': exact_time,
                'df_heuristic': df_heuristic.to_dict('records'),
                'time_heuristic': heuristic_time
            }
            self.finished.emit(final_results)

        except Exception as e:
            self.finished.emit({'error': f'Ocorreu um erro: {e}'})

# --- WIDGET DE GRÁFICO (sem alterações) ---
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)

# --- JANELA PRINCIPAL (UI com a correção dos sliders) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard de Validação e Análise")
        self.setGeometry(100, 100, 1400, 800)
        self._setup_ui()
        self.worker_thread = None
        self.populate_instances()

    def _setup_ui(self):
        main_layout = QHBoxLayout()
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.StyledPanel)
        control_frame.setFixedWidth(350)
        control_layout = QVBoxLayout(control_frame)

        title_font = QFont(); title_font.setBold(True); title_font.setPointSize(12)
        control_title = QLabel("Validação de Heurística")
        control_title.setFont(title_font)
        control_layout.addWidget(control_title)
        
        # (Widgets de instância sem alterações)
        self.generate_button = QPushButton("Gerar/Atualizar Instâncias")
        self.generate_button.clicked.connect(self.generate_instances)
        control_layout.addWidget(self.generate_button)
        control_layout.addWidget(QLabel("Selecione a instância:"))
        self.instance_combo = QComboBox()
        control_layout.addWidget(self.instance_combo)
        control_layout.addWidget(QFrame(frameShape=QFrame.HLine))

        # --- CORREÇÃO: Layout em Grade para os Parâmetros do AG ---
        ag_title = QLabel("Parâmetros do Algoritmo Genético")
        ag_title.setFont(title_font)
        control_layout.addWidget(ag_title)

        # Usando um layout de grade para alinhar labels e widgets
        params_layout = QGridLayout()
        
        # Tamanho da População
        params_layout.addWidget(QLabel("Tamanho da População:"), 0, 0)
        self.pop_spinbox = QSpinBox()
        self.pop_spinbox.setRange(50, 5000); self.pop_spinbox.setValue(200); self.pop_spinbox.setSingleStep(50)
        params_layout.addWidget(self.pop_spinbox, 0, 1)
        
        # Número de Gerações
        params_layout.addWidget(QLabel("Número de Gerações:"), 1, 0)
        self.ngen_spinbox = QSpinBox()
        self.ngen_spinbox.setRange(10, 2000); self.ngen_spinbox.setValue(100); self.ngen_spinbox.setSingleStep(10)
        params_layout.addWidget(self.ngen_spinbox, 1, 1)

        # Prob. de Crossover
        params_layout.addWidget(QLabel("Prob. de Crossover (%):"), 2, 0)
        self.cxpb_slider = QSlider(Qt.Horizontal)
        self.cxpb_slider.setRange(0, 100); self.cxpb_slider.setValue(70)
        self.cxpb_label = QLabel(f"{self.cxpb_slider.value()}%") # Label para mostrar o valor
        self.cxpb_slider.valueChanged.connect(lambda val: self.cxpb_label.setText(f"{val}%")) # Conecta o slider ao label
        params_layout.addWidget(self.cxpb_slider, 2, 1)
        params_layout.addWidget(self.cxpb_label, 2, 2)

        # Prob. de Mutação
        params_layout.addWidget(QLabel("Prob. de Mutação (%):"), 3, 0)
        self.mutpb_slider = QSlider(Qt.Horizontal)
        self.mutpb_slider.setRange(0, 100); self.mutpb_slider.setValue(20)
        self.mutpb_label = QLabel(f"{self.mutpb_slider.value()}%") # Label para mostrar o valor
        self.mutpb_slider.valueChanged.connect(lambda val: self.mutpb_label.setText(f"{val}%")) # Conecta o slider ao label
        params_layout.addWidget(self.mutpb_slider, 3, 1)
        params_layout.addWidget(self.mutpb_label, 3, 2)
        
        control_layout.addLayout(params_layout)
        # --- FIM DA CORREÇÃO ---

        self.run_button = QPushButton("Executar Validação")
        self.run_button.setStyleSheet("background-color: #007bff; color: white; padding: 10px; margin-top: 10px;")
        self.run_button.clicked.connect(self.start_validation)
        control_layout.addWidget(self.run_button)
        
        control_layout.addStretch()

        # (Painel de Resultados e montagem final sem alterações)
        results_layout = QVBoxLayout()
        self.canvas = MplCanvas(self, width=8, height=5, dpi=100)
        self.toolbar = NavigationToolbar(self.canvas, self)
        results_layout.addWidget(self.toolbar)
        results_layout.addWidget(self.canvas)
        time_layout = QHBoxLayout()
        self.exact_time_label = QLabel("Tempo Exato: -- s")
        self.heuristic_time_label = QLabel("Tempo Heurística: -- s")
        time_layout.addWidget(self.exact_time_label)
        time_layout.addWidget(self.heuristic_time_label)
        results_layout.addLayout(time_layout)
        tables_layout = QHBoxLayout()
        self.exact_table = QTableWidget()
        self.heuristic_table = QTableWidget()
        tables_layout.addWidget(self.exact_table)
        tables_layout.addWidget(self.heuristic_table)
        results_layout.addLayout(tables_layout)
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Pronto.")
        self.progress_bar = QProgressBar()
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        results_layout.addLayout(status_layout)
        main_layout.addWidget(control_frame)
        main_layout.addLayout(results_layout)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    # (start_validation e outras funções permanecem as mesmas)
    def start_validation(self):
        selected_file = self.instance_combo.currentText()
        if not selected_file or "Nenhuma" in selected_file:
            self.status_label.setText("Erro: Nenhuma instância selecionada.")
            return
        self.run_button.setEnabled(False)
        self.run_button.setText("Executando...")
        self.progress_bar.setRange(0, 0)
        pop_size = self.pop_spinbox.value()
        ngen = self.ngen_spinbox.value()
        cxpb = self.cxpb_slider.value() / 100.0
        mutpb = self.mutpb_slider.value() / 100.0
        self.worker_thread = ValidationWorker(selected_file, pop_size, ngen, cxpb, mutpb)
        self.worker_thread.status_update.connect(self.update_status)
        self.worker_thread.finished.connect(self.display_results)
        self.worker_thread.start()

    def display_results(self, results):
        self.run_button.setEnabled(True)
        self.run_button.setText("Executar Validação")
        self.progress_bar.setRange(0, 100); self.progress_bar.setValue(100)
        self.status_label.setText("Análise Comparativa Concluída!")
        if 'error' in results:
            self.status_label.setText(f"Erro: {results['error']}")
            return
        self.exact_time_label.setText(f"Tempo Exato: {results['time_exact']:.2f} s")
        self.heuristic_time_label.setText(f"Tempo Heurística: {results['time_heuristic']:.2f} s")
        df_exact = pd.DataFrame(results['df_exact'])
        df_heuristic = pd.DataFrame(results['df_heuristic'])
        self.canvas.axes.clear()
        if not df_exact.empty:
            self.canvas.axes.plot(df_exact['num_clusters_f2'], df_exact['disagreement_f1'], 
                                marker='*', linestyle='--', label='Ótima (Exato)')
        if not df_heuristic.empty:
            self.canvas.axes.scatter(df_heuristic['num_clusters_f2'], df_heuristic['disagreement_f1'], 
                                    marker='o', label='Aproximada (AG)', alpha=0.8, s=100)
        self.canvas.axes.set_title("Comparativo de Fronteiras de Pareto")
        self.canvas.axes.set_xlabel("Número de Clusters (f2)")
        self.canvas.axes.set_ylabel("Desequilíbrio (f1)")
        self.canvas.axes.grid(True)
        self.canvas.axes.legend()
        self.canvas.draw()
        self._populate_table(self.exact_table, df_exact, "Fronteira Ótima (Exato)")
        self._populate_table(self.heuristic_table, df_heuristic, "Fronteira Encontrada (AG)")

    def populate_instances(self):
        self.instance_combo.clear()
        synthetic_files = sorted(glob.glob("data/run1_*.csv"))
        if synthetic_files:
            self.instance_combo.addItems(synthetic_files)
            self.run_button.setEnabled(True)
        else:
            self.instance_combo.addItem("Nenhuma instância encontrada"); self.run_button.setEnabled(False)
    
    def generate_instances(self):
        self.status_label.setText("Gerando instâncias..."); QApplication.processEvents()
        generate_multigraph_instances()
        self.status_label.setText("Instâncias geradas."); self.populate_instances()

    def update_status(self, text):
        self.status_label.setText(text)

    def _populate_table(self, table_widget, df, title):
        table_widget.clear(); table_widget.setRowCount(0); table_widget.setColumnCount(0)
        if df.empty: return
        table_widget.setRowCount(len(df) + 1)
        table_widget.setColumnCount(len(df.columns))
        title_item = QTableWidgetItem(title); title_font = QFont(); title_font.setBold(True)
        title_item.setFont(title_font); table_widget.setItem(0, 0, title_item)
        table_widget.setSpan(0, 0, 1, len(df.columns))
        table_widget.setHorizontalHeaderLabels(df.columns)
        for i, row in df.iterrows():
            for j, val in enumerate(row):
                table_widget.setItem(i + 1, j, QTableWidgetItem(f"{val:.4f}" if isinstance(val, float) else str(val)))
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())