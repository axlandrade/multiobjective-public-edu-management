# app_desktop.py

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QProgressBar, QLabel
from PySide6.QtCore import QThread, Signal
import time

# Vamos simular sua função demorada
# from experiments.heuristic.run_genetic_algorithm import run_ga_experiment

# --- A Thread de Trabalho ---
class WorkerThread(QThread):
    progress = Signal(int, str)  # Sinal para atualizar o progresso (percentual, texto)
    finished = Signal(str)       # Sinal para indicar que terminou (com uma mensagem de resultado)

    def __init__(self, generations):
        super().__init__()
        self.generations = generations

    def run(self):
        """Esta função é executada na thread separada."""
        for gen in range(1, self.generations + 1):
            time.sleep(0.1) # Simula o trabalho de uma geração
            
            # Emite um sinal para a UI
            self.progress.emit(int((gen / self.generations) * 100), f"Processando geração {gen}/{self.generations}...")
        
        # Emite o sinal de finalização
        self.finished.emit("Análise concluída com sucesso!")


# --- A Janela Principal da UI ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard de Análise")
        self.setGeometry(100, 100, 400, 200)

        # Widgets da UI
        self.layout = QVBoxLayout()
        self.label = QLabel("Clique no botão para iniciar a análise.")
        self.button = QPushButton("Executar Análise")
        self.progress_bar = QProgressBar()

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.progress_bar)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        # Conectar o clique do botão à função que inicia o trabalho
        self.button.clicked.connect(self.start_analysis)
        self.worker = None

    def start_analysis(self):
        self.button.setEnabled(False)
        self.label.setText("Iniciando a execução...")
        
        # Cria e inicia a thread de trabalho
        self.worker = WorkerThread(generations=100)
        
        # Conecta os sinais da thread às funções (slots) da UI
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finish)
        
        self.worker.start()

    def update_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.label.setText(text)

    def on_finish(self, message):
        self.label.setText(message)
        self.progress_bar.setValue(100)
        self.button.setEnabled(True)


# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())