# Detecção de Redes de Corrupção com Otimização Multiobjetivo em Multigrafos

Este projeto é a implementação computacional da dissertação de mestrado "Otimização Multiobjetivo em Multigrafos para Detecção de Redes de Corrupção: Uma Análise Comparativa entre Métodos Exatos e Heurísticos". O objetivo é aplicar o problema de *Correlation Clustering* (CC) em uma rede de contratos públicos modelada como um multigrafo para identificar potenciais grupos de risco.

O framework implementa duas abordagens de solução e uma interface gráfica interativa para análise.

## ✨ Funcionalidades

- **Modelo Exato (PLI):** Uma formulação de Programação Linear Inteira utilizando `gurobipy` para encontrar a solução ótima do problema. Ideal para validação em instâncias de pequena escala.
- **Modelo Heurístico (AG):** Uma meta-heurística baseada no Algoritmo Genético Multiobjetivo (NSGA-II) com a biblioteca `DEAP`, projetada para escalar em redes de grande porte.
- **Interface Gráfica Interativa:** Um dashboard desenvolvido com **Streamlit** que permite executar ambos os modelos, ajustar parâmetros, visualizar a fronteira de Pareto e inspecionar os clusters resultantes de forma interativa.
- **Geração de Dados:** Scripts para gerar instâncias sintéticas baseadas no trabalho de Ponciano (2017) e para processar dados reais de contratos.

## 📂 Estrutura do Projeto

O projeto está organizado da seguinte forma:

```
    .
    +-- .devcontainer/
    |   +-- devcontainer.json   # Configuração do ambiente de desenvolvimento Docker
    +-- data/
    |   +-- contratos_enriquecidos.csv # (Exemplo) Dados brutos de contratos
    |   +-- ...                   # Arquivos de rede gerados (.csv)
    +-- experiments/
    |   +-- exact/                # Scripts para o modelo exato
    |   +-- heuristic/            # Scripts para o modelo heurístico
    +-- src/
    |   +-- graph_constructor.py  # Módulo para construir o grafo a partir dos dados
    |   +-- optimization_model.py # Implementação do modelo exato (PLI)
    |   +-- genetic_algorithm.py  # Implementação da lógica do AG
    |   +-- ...
    +-- app.py                    # Script principal da interface gráfica (Streamlit)
    +-- requirements.txt          # Dependências Python
    +-- README.md                 # Este arquivo
```

## 🚀 Como Começar

A maneira recomendada de executar este projeto é utilizando o ambiente de desenvolvimento em contêiner (Dev Container) com VS Code, que garante que todas as dependências e configurações estejam corretas.

### Pré-requisitos

1.  **Docker Desktop** instalado.
2.  **Visual Studio Code** com a extensão [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

### Instalação

1.  Clone este repositório:
    ```bash
    git clone https://github.com/axlandrade/dynamic-corruption-detection.git
    cd dynamic-corruption-detection
    ```
2.  Abra a pasta do projeto no VS Code.
3.  O VS Code detectará o arquivo `.devcontainer/devcontainer.json` e sugerirá reabrir o projeto em um contêiner. Clique em **"Reopen in Container"**.
4.  Aguarde enquanto o ambiente é construído. Os pacotes do `requirements.txt` serão instalados automaticamente.

## 💻 Como Usar

Existem duas maneiras principais de interagir com o projeto: através da interface gráfica (recomendado) ou diretamente pela linha de comando.

### 1. Usando a Interface Gráfica (Streamlit)

Esta é a forma mais fácil e visual de executar os experimentos e analisar os resultados.

1.  Abra um terminal no VS Code (que já estará dentro do contêiner).
2.  Execute o seguinte comando na pasta raiz do projeto:

    ```bash
    streamlit run app.py
    ```
3.  Seu navegador abrirá automaticamente com o dashboard, onde você poderá:
    - Fazer o upload de um arquivo de rede `.csv`.
    - Escolher entre a análise **Exata** ou **Heurística**.
    - Ajustar os parâmetros específicos de cada modelo.
    - Executar a análise e visualizar os resultados interativamente.

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
    Execute o script na pasta `experiments/heuristic/` passando o caminho do arquivo de dados.
    ```bash
    python experiments/heuristic/run_genetic_algorithm.py --data data/run1_P4_k5.csv
    ```

-   **Modelo Exato (PLI):**
    O script `run_sintetic.sh` é um exemplo de como executar o modelo exato para todas as instâncias sintéticas com diferentes valores de lambda.
    ```bash
    bash run_sintetic.sh
    ```
    Para executar em um arquivo específico (como os dados reais), use o script dedicado:
    ```bash
    python experiments/exact/run_exact_real.py --lambda_weight 0.5 --time_limit 3600
    ```