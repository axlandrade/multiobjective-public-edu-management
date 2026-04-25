# Otimização Multiobjetivo na Gestão Pública e Educacional

Este projeto é a implementação computacional da dissertação de mestrado *"Abordagens de Otimização Multiobjetivo na Gestão Pública e Educacional: Resolução de Demandas Integradas e Detecção de Padrões"*. 

O repositório abriga formulações matemáticas e heurísticas aplicadas a dois grandes contextos de tomada de decisão:

1. **Gestão Pública:** Detecção de redes de corrupção em licitações modeladas como multigrafos sinalizados, utilizando o problema de *Correlation Clustering* (CC) probabilístico para identificar grupos de risco.
2. **Gestão Educacional:** Integração multiobjetivo das rotinas operacionais de universidades públicas, acoplando a alocação de turmas em salas de aula (WSAC) ao planejamento nutricional de restaurantes universitários (WSMS).

O framework implementa abordagens exatas e heurísticas para a construção de Fronteiras de Pareto, visando fornecer suporte robusto à tomada de decisão de gestores.

## Funcionalidades

- **Modelos Exatos (PLI/MILP):** Formulações de Programação Linear Inteira e Mista utilizando `gurobipy` para encontrar soluções ótimas em redes menores e cenários específicos.
- **Modelos Heurísticos (AG):** Meta-heurísticas baseadas no Algoritmo Genético Multiobjetivo (NSGA-II) utilizando a biblioteca `DEAP`, projetadas para contornar a explosão combinatória e escalar para instâncias de grande porte.
- **Análise de Fronteiras de Pareto:** Geração de conjuntos de soluções não dominadas, permitindo avaliar o *trade-off* entre interpretabilidade vs. desequilíbrio estrutural (Gestão Pública) e cobertura discente vs. custos nutricionais (Gestão Educacional).
- **Interface Gráfica Desktop (Em desenvolvimento):** Dashboard desenvolvido com **PySide6 (Qt for Python)** para gerenciar as execuções, instâncias e visualizar os resultados de forma interativa.

## Estrutura Inicial do Projeto

A arquitetura do projeto divide as lógicas dos dois domínios da dissertação:

```text
    .
    ├── data/
    │   ├── public_management/    # Instâncias sintéticas e reais de licitações
    │   └── edu_management/       # Dados de disciplinas, salas e parâmetros nutricionais
    ├── src/
    │   ├── public_management/    # Lógica de grafos, PLI e NSGA-II para detecção de corrupção
    │   ├── edu_management/       # Formulação integrada WSAC-WSMS
    │   ├── core/                 # Módulos compartilhados (ex: utilitários de Pareto)
    │   └── gui/                  # Componentes da interface gráfica PySide6
    ├── requirements.txt          # Dependências Python
    └── README.md                 # Este arquivo
```

## Configuração do Ambiente Local

Este projeto utiliza um ambiente virtual Python (`venv`) para gerenciar as dependências de forma isolada.

### Pré-requisitos

1. **Python 3.9+** instalado no seu sistema.
2. **Git** para clonar o repositório.
3. **Gurobi Optimizer:** É necessária uma licença válida do solver Gurobi para executar as abordagens exatas. A [licença acadêmica gratuita](https://www.gurobi.com/academia/academic-program-and-licenses/) é recomendada e atende aos requisitos estruturais dos modelos.

### Instalação

1. Clone este repositório:
   ```bash
   git clone https://github.com/axlandrade/multiobjective-public-edu-management.git
   cd multiobjective-public-edu-management
   ```

2. Crie e ative um ambiente virtual:
   ```bash
   # Cria o ambiente
   python -m venv .venv

   # Ativa o ambiente (Windows PowerShell)
   .\.venv\Scripts\Activate.ps1

   # Ativa o ambiente (Linux/macOS/Git Bash)
   source .venv/bin/activate
   ```

3. Instale as dependências necessárias:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

*(Nota: As instruções detalhadas de execução dos experimentos via linha de comando ou interface gráfica serão documentadas futuramente, conforme a consolidação do programa final).*
