# Manual explicativo do projeto

Projeto: `multiobjective-public-edu-management`

Este documento explica a organizacao do repositorio, o papel de cada modulo e o
fluxo de execucao dos modelos de otimizacao multiobjetivo aplicados a gestao
publica e gestao educacional.

## 1. Objetivo geral

O projeto implementa experimentos computacionais para dois dominios:

1. Gestao publica: deteccao de padroes de risco em contratos publicos usando
   multigrafos e correlation clustering multiobjetivo.
2. Gestao educacional: integracao entre alocacao de turmas em salas de aula
   (WSAC) e planejamento de refeicoes do restaurante universitario (WSMS).

Nos dois casos, a ideia central e produzir solucoes que equilibrem objetivos
conflitantes. Em vez de procurar apenas uma resposta unica, o projeto permite
explorar fronteiras de Pareto ou diferentes pesos `lambda`.

## 2. Estrutura de pastas

```text
.
|-- main.py
|-- requirements.txt
|-- setup.py
|-- Dockerfile
|-- src/
|   |-- public_management/
|   |-- edu_management/
|   |-- core/
|-- experiments/
|   |-- public_management/
|   |-- edu_management/
|-- gui/
|-- Documentos/
```

### `src/public_management`

Contem a logica do dominio de gestao publica.

- `graph_constructor.py`: le um CSV de contratos/relacoes e cria um
  `networkx.MultiGraph`.
- `create_real_network.py`: transforma dados brutos de contratos em uma rede
  padronizada com `node_1`, `node_2`, `positive_prob` e `weight`.
- `optimization_model.py`: modelo exato via OR-Tools/SCIP para correlation
  clustering multiobjetivo.
- `optimization_model_bak.py`: versao legada em Gurobi, mantida como referencia.
- `genetic_algorithm.py`: configuracao do NSGA-II via DEAP para gerar solucoes
  aproximadas em instancias maiores.
- `instance_generator.py`: gera instancias sinteticas de multigrafos.
- `visualizer.py`: salva imagens dos grafos particionados em clusters.

### `src/edu_management`

Contem a logica do dominio de gestao educacional.

- `optimization_model.py`: modelo exato via OR-Tools que integra alocacao de
  disciplinas e planejamento alimentar.
- `optimization_model_bak.py`: versao legada em Gurobi que tambem retorna grade
  horaria e cardapio detalhado.
- `genetic_algorithm.py`: configuracao do NSGA-II para evoluir grades de
  horarios e avaliar custo do restaurante universitario.

### `experiments`

Scripts prontos para execucoes experimentais.

- `experiments/public_management/run_exact.py`: executa o modelo exato em dados
  reais de contratos.
- `experiments/public_management/run_heuristic.py`: executa o algoritmo genetico
  NSGA-II em uma rede real ou sintetica.
- `experiments/edu_management/run_exact.py`: faz varredura de valores `lambda`
  no modelo educacional exato.
- `experiments/edu_management/run_heuristic.py`: gera fronteira de Pareto
  educacional via NSGA-II.
- `experiments/edu_management/cluster_pareto.py`: agrupa solucoes de Pareto em
  perfis gerenciais usando uma variante rapida de correlation clustering.

### `gui`

`gui/dashboard_web.py` implementa uma dashboard web em Streamlit para executar
analises, visualizar fronteiras, processar dados reais e baixar resultados.

## 3. Fluxo da gestao publica

### Entrada esperada

O modelo trabalha com um CSV no formato:

```text
node_1,node_2,positive_prob,weight
```

- `node_1`: primeiro ator da relacao, por exemplo orgao publico.
- `node_2`: segundo ator da relacao, por exemplo fornecedor.
- `positive_prob`: probabilidade/score de risco associado a relacao.
- `weight`: peso da relacao na funcao objetivo.

### Montagem do grafo

`build_multigraph_from_csv` le o CSV, remove linhas incompletas, padroniza os
nomes dos nos e cria um `MultiGraph`. O uso de multigrafo e importante porque
dois atores podem ter varios contratos entre si, e cada contrato deve ser
preservado como uma aresta paralela.

### Modelo exato

`solve_multigraph_cc` formula o problema como programacao inteira:

- `y[i]`: indica se o no `i` e representante de cluster.
- `z[i,j]`: indica se o no `j` pertence ao cluster representado por `i`.
- `w[i,j,k]`: lineariza a decisao de dois nos estarem juntos no cluster `k`.
- `s[i,j]`: indica se dois nos estao no mesmo cluster.

Objetivos:

- `f1`: minimizar o desequilibrio esperado da particao.
- `f2`: minimizar o numero de clusters.
- `Z`: combinacao ponderada `lambda * f1 + (1 - lambda) * f2`.

Quando `lambda` se aproxima de 1, o modelo privilegia reduzir o desacordo. Quando
se aproxima de 0, privilegia reduzir a quantidade de clusters.

### Algoritmo genetico

O NSGA-II representa cada solucao como um cromossomo. Cada gene informa qual no
sera o representante de cluster daquele item. A avaliacao calcula:

- custo de separar nos que deveriam ficar juntos;
- custo de manter juntos nos que deveriam ficar separados;
- numero total de representantes distintos.

A funcao pre-agrega arestas paralelas para acelerar a avaliacao de muitas
solucoes durante a evolucao.

## 4. Fluxo da gestao educacional

### Problema integrado

O dominio educacional une duas decisoes:

1. Alocar disciplinas em salas, dias e turnos.
2. Dimensionar refeicoes do restaurante universitario de acordo com os alunos
   presentes.

### Modelo exato

`solve_integrated_edu_management` usa:

- `x[d,r,day,shift]`: disciplina `d` alocada na sala `r`, dia e turno.
- `y[m,day,shift]`: quantidade do alimento `m` servida naquele dia e turno.

Restricoes principais:

- cada disciplina ocorre no maximo uma vez;
- a capacidade da sala deve comportar os alunos matriculados;
- uma sala nao recebe duas disciplinas no mesmo horario;
- alunos em aula geram demanda minima de refeicoes;
- as calorias ofertadas devem atingir o minimo definido.

Objetivos:

- maximizar alunos cobertos;
- minimizar custo total do restaurante universitario.

Como o solver minimiza, a cobertura aparece com sinal negativo na funcao
objetivo ponderada.

### Algoritmo genetico

No NSGA-II educacional, o cromossomo tem uma posicao por disciplina. Cada valor e:

- um `slot_id`, representando dia, turno e sala;
- `-1`, quando a disciplina nao foi alocada.

A aptidao penaliza solucoes invalidas, como duas disciplinas no mesmo slot, mas
mantem as metricas reais para relatorio da fronteira de Pareto.

## 5. Dashboard web

A interface atual fica em `gui/dashboard_web.py` e usa Streamlit. Ela organiza o
projeto em fluxos web:

- Visao geral: resume o framework, solver e heuristica usados.
- Processar contratos: converte CSV bruto em rede de entrada.
- Publica - exato: executa o modelo OR-Tools de correlation clustering.
- Publica - NSGA-II: executa a heuristica evolutiva e gera a fronteira.
- Educacional - exato: faz a varredura de lambdas no modelo WSAC-WSMS.

Para abrir:

```powershell
streamlit run gui/dashboard_web.py
```

Tambem e possivel abrir a dashboard via Docker:

```powershell
docker build -t multiobjective-management .
docker run --rm -p 8501:8501 multiobjective-management
```

A imagem expõe a porta `8501`, executa `streamlit run gui/dashboard_web.py` por
padrao e inclui um healthcheck para a rota interna do Streamlit.

## 6. Como instalar

No PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

## 7. Exemplos de execucao

### Modelo publico exato via `main.py`

```powershell
python main.py --data data\rede_real_input.csv --output_dir results --lambda_weight 0.5 --time_limit 3600
```

### Heuristica de gestao publica

```powershell
python experiments\public_management\run_heuristic.py --data data\rede_real_input.csv --output_dir results_real_data
```

### Varredura exata educacional

```powershell
python experiments\edu_management\run_exact.py
```

### Heuristica educacional

```powershell
python experiments\edu_management\run_heuristic.py
```

### Agrupamento da fronteira educacional

```powershell
python experiments\edu_management\cluster_pareto.py
```

### Docker

```powershell
docker build -t multiobjective-management .
docker run --rm -p 8501:8501 multiobjective-management
```

## 8. Saidas geradas

O projeto pode gerar:

- CSVs com clusters encontrados;
- JSONs com particoes ou estatisticas;
- PNGs de visualizacao de grafos;
- CSVs de fronteiras de Pareto;
- relatorios de perfis gerenciais.

As pastas de saida mais comuns sao `results_edu`, `results_real_data`,
`results_exact_real_ortools` e diretorios informados por `--output_dir`.

## 9. Observacoes importantes

- Os arquivos legados `*_bak.py` foram removidos para manter apenas os modelos
  ativos baseados em OR-Tools.
- O arquivo `.devcontainer/devcontainer.json` nao foi comentado internamente
  porque JSON padrao nao aceita comentarios.
- A antiga GUI desktop em PySide6 foi removida para simplificar a manutencao e
  concentrar a experiencia em uma dashboard web.
- Para instancias grandes, prefira os scripts heuristicas com NSGA-II. O modelo
  exato pode crescer rapidamente em numero de variaveis e restricoes.

## 10. Resumo conceitual

O repositorio e um laboratorio computacional de apoio a decisao. Ele modela
problemas reais como estruturas matematicas, resolve esses problemas por metodos
exatos ou heuristicas evolutivas, e transforma os resultados em tabelas,
fronteiras e visualizacoes para interpretacao gerencial.
