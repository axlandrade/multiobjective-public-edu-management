# Otimizacao multiobjetivo na gestao publica e educacional

Este repositorio implementa modelos exatos e heuristicas para apoiar decisoes
multiobjetivo em dois dominios:

1. **Gestao publica:** deteccao de padroes de risco em contratacoes publicas
   modeladas como multigrafos, usando correlation clustering probabilistico.
2. **Gestao educacional:** integracao entre alocacao de disciplinas em salas
   (WSAC) e planejamento de refeicoes do restaurante universitario (WSMS).

O projeto usa Python, OR-Tools/SCIP para modelos exatos e DEAP/NSGA-II para
heuristicas evolutivas.

## Dashboard web

A antiga interface desktop em PySide6 foi substituida por uma dashboard web em
Streamlit:

```powershell
streamlit run gui/dashboard_web.py
```

A dashboard permite:

- processar CSV bruto de contratos em uma rede padronizada;
- coletar contratos diretamente da API do Portal da Transparencia por lista de
  CNPJs;
- enriquecer contratos coletados e gerar a rede de entrada automaticamente;
- executar o modelo exato de gestao publica;
- executar a heuristica NSGA-II de gestao publica;
- executar o modelo integrado WSAC+WSMS exato e por NSGA-II;
- visualizar fronteiras de Pareto;
- executar uma varredura educacional exata em instancia sintetica;
- baixar CSVs de resultados.

## Estrutura

```text
.
|-- main.py
|-- requirements.txt
|-- setup.py
|-- Dockerfile
|-- gui/
|   |-- dashboard_web.py
|-- src/
|   |-- public_management/
|   |-- edu_management/
|-- experiments/
|   |-- public_management/
|   |-- edu_management/
|-- Documentos/
```

## Principais modulos

### `src/public_management`

- `graph_constructor.py`: constroi um `networkx.MultiGraph` a partir de CSV.
- `create_real_network.py`: transforma contratos brutos em arestas com score de
  risco.
- `transparency_collector.py`: coleta contratos do Portal da Transparencia por
  CNPJ e aplaina os dados aninhados da API.
- `optimization_model.py`: resolve o modelo exato de correlation clustering com
  OR-Tools.
- `genetic_algorithm.py`: configura o NSGA-II para gerar fronteiras aproximadas.
- `instance_generator.py`: cria instancias sinteticas.
- `visualizer.py`: salva visualizacoes estaticas dos grafos.

### `src/edu_management`

- `optimization_model.py`: resolve o modelo integrado WSAC-WSMS com OR-Tools.
- `genetic_algorithm.py`: configura a heuristica NSGA-II educacional.

### `experiments`

Scripts de linha de comando para execucoes reprodutiveis dos modelos exatos,
heuristicos e agrupamentos de solucoes.

## Instalacao

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

## Exemplos de execucao

Modelo publico exato:

```powershell
python main.py --data data\rede_real_input.csv --output_dir results --lambda_weight 0.5 --time_limit 3600
```

Heuristica de gestao publica:

```powershell
python experiments\public_management\run_heuristic.py --data data\rede_real_input.csv --output_dir results_real_data
```

Varredura educacional exata:

```powershell
python experiments\edu_management\run_exact.py
```

Dashboard web:

```powershell
streamlit run gui/dashboard_web.py
```

## Docker

Build da imagem:

```powershell
docker build -t multiobjective-management .
```

Executar a dashboard em `http://localhost:8501`:

```powershell
docker run --rm -p 8501:8501 multiobjective-management
```

O `Dockerfile` instala as dependencias de `requirements.txt`, instala o projeto
em modo editavel e inicia a dashboard Streamlit por padrao.
