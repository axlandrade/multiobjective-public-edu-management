# Detecção de Redes de Corrupção com Otimização Multiobjetivo em Multigrafos

Este projeto é a implementação computacional da dissertação de mestrado "Otimização Multiobjetivo em Multigrafos para Detecção de Redes de Corrupção: Uma Análise Comparativa entre Métodos Exatos e Heurísticos". O objetivo é aplicar o problema de *Correlation Clustering* (CC) em uma rede de contratos públicos modelada como um multigrafo para identificar potenciais grupos de risco.

O framework implementa duas abordagens de solução e uma interface gráfica desktop para uma análise robusta e interativa.

## Funcionalidades

- **Modelo Exato (PLI):** Uma formulação de Programação Linear Inteira utilizando `gurobipy` para encontrar a solução ótima do problema.
- **Modelo Heurístico (AG):** Uma meta-heurística baseada no Algoritmo Genético Multiobjetivo (NSGA-II) com a biblioteca `DEAP`, projetada para escalar em redes de grande porte.
- **Interface Gráfica Desktop:** Um dashboard desenvolvido com **PySide6 (Qt for Python)**, uma aplicação desktop nativa e robusta. É ideal para gerenciar tarefas computacionais de longa duração sem congelar ou perder a sessão, permitindo o acompanhamento do progresso em tempo real.
- **Geração de Dados:** Scripts para gerar instâncias sintéticas baseadas no trabalho de Ponciano (2017) e para processar dados reais de contratos.

## Estrutura do Projeto

O projeto está organizado da seguinte forma:

```
    .
    ├── data/
    │   ├── contratos_enriquecidos.csv # (Exemplo) Dados brutos de contratos
    │   └── ...                   # Arquivos de rede gerados (.csv)
    ├── experiments/
    │   ├── exact/                # Scripts para o modelo exato
    │   └── heuristic/            # Scripts para o modelo heurístico
    ├── src/
    │   ├── graph_constructor.py  # Módulo para construir o grafo a partir dos dados
    │   ├── optimization_model.py # Implementação do modelo exato (PLI)
    │   ├── genetic_algorithm.py  # Implementação da lógica do AG
    │   └── ...
    ├── app.py                    # Script principal da interface gráfica (PySide6)
    ├── requirements.txt          # Dependências Python
    └── README.md                 # Este arquivo
```

## Configuração do Ambiente Local

Este projeto utiliza um ambiente virtual Python (`venv`) para gerenciar suas dependências de forma isolada.

### Pré-requisitos

1.  **Python 3.9+** instalado em seu sistema.
2.  **Git** para clonar o repositório.
3.  **Gurobi Optimizer:** Uma licença do Gurobi (a [licença acadêmica gratuita](https://www.gurobi.com/academia/academic-program-and-licenses/) é suficiente e recomendada) é necessária para executar o modelo exato.

### Instalação

1.  Clone este repositório:
    ```bash
    git clone [https://github.com/axlandrade/dynamic-corruption-detection.git](https://github.com/axlandrade/dynamic-corruption-detection.git)
    cd dynamic-corruption-detection
    ```

2.  Crie e ative um ambiente virtual:
    ```bash
    # Cria o ambiente
    python -m venv .venv

    # Ativa o ambiente (Windows PowerShell)
    .\.venv\Scripts\Activate.ps1

    # Ativa o ambiente (Linux/macOS/Git Bash)
    source .venv/bin/activate
    ```

3.  Instale as dependências Python necessárias:
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

## Como Usar

### 1. Usando a Interface Gráfica (Recomendado)

A aplicação desktop é a forma mais completa de interagir com os experimentos.

1.  Certifique-se de que seu ambiente virtual (`.venv`) está ativado.
2.  Execute o seguinte comando na pasta raiz do projeto:

    ```bash
    python app.py
    ```
3.  A janela do dashboard abrirá, onde você poderá:
    - Gerar as instâncias sintéticas para validação.
    - Selecionar uma instância e ajustar os parâmetros do Algoritmo Genético.
    - Executar o **modo de validação**, que roda o modelo exato e o heurístico em sequência e compara as fronteiras de Pareto.
    - Acompanhar o progresso em tempo real através da barra de status.

### 2. Usando a Linha de Comando

Para execuções em lote ou testes específicos, você pode usar os scripts diretamente.

#### Preparando os Dados

-   **Para gerar as instâncias sintéticas:**
    ```bash
    python src/instance_generator.py
    ```
-   **Para processar os dados reais e criar o arquivo de rede:**
    ```bash
    python src/create_real_network.py
    ```

#### Executando os Experimentos

-   **Modelo Heurístico (AG):**
    ```bash
    python experiments/heuristic/run_genetic_algorithm.py --data data/run1_P4_k5.csv
    ```

-   **Modelo Exato (PLI):**
    ```bash
    python experiments/exact/run_exact_real.py --lambda_weight 0.5 --time_limit 3600