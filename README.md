# Análise Dinâmica de Redes de Corrupção com Equilíbrio Estrutural em Multigrafos

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

> Modelo de otimização matemática para análise dinâmica de redes de corrupção, usando a teoria de Equilíbrio Estrutural em multigrafos.

Este repositório contém o código e a documentação da pesquisa desenvolvida na dissertação de mestrado de **Axl Silva de Andrade**, no âmbito do Programa de Pós-Graduação em Modelagem Matemática e Computacional da UFRRJ.

---

## Tabela de Conteúdos

- [Sobre o Projeto](#sobre-o-projeto)
- [Principais Conceitos](#principais-conceitos)
- [Começando](#começando)
  - [Pré-requisitos](#pré-requisitos)
  - [Instalação](#instalação)
- [Como Usar](#como-usar)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Licença](#licença)
- [Contato e Citação](#contato-e-citação)

---

## Sobre o Projeto

A detecção de corrupção em licitações públicas é um desafio complexo. Modelos baseados em grafos simples, que representam a relação entre duas entidades com uma única aresta, perdem informações valiosas sobre a dinâmica e a frequência das interações contratuais.

Este projeto propõe uma extensão do modelo de **Equilíbrio Estrutural Probabilístico** para **multigrafos**, permitindo uma representação mais fiel de redes de licitações, onde múltiplos contratos entre as mesmas entidades são comuns. O objetivo é desenvolver um modelo de IA, baseado em otimização matemática, capaz de identificar padrões dinâmicos e a evolução de clusters de *State Capture*.

---

## Principais Conceitos

* **Equilíbrio Estrutural:** Teoria da psicologia social que postula que redes tendem a se organizar em grupos com coesão interna e hostilidade externa.
* **Correlation Clustering (CC):** Problema de otimização que busca a melhor partição de um grafo para minimizar o "desequilíbrio" (arestas positivas entre clusters e negativas dentro de clusters).
* **Multigrafo:** Estrutura de grafo que permite a existência de múltiplas arestas paralelas entre o mesmo par de vértices, ideal para modelar contratos repetidos.

---

## Começando

Siga estas instruções para obter uma cópia do projeto e executá-lo em sua máquina local.

### Pré-requisitos

* Python 3.9+
* Um solver de otimização, como Gurobi ou CPLEX, instalado e com uma licença válida.

### Instalação

1.  **Clone o repositório:**
    ```sh
    git clone [https://github.com/](https://github.com/)[axlandrade]/dynamic-corruption-detection.git
    cd dynamic-corruption-detection
    ```

2.  **Crie e ative um ambiente virtual:**
    ```sh
    python -m venv venv
    # No Windows:
    venv\Scripts\activate
    # No Linux/Mac:
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    (Você precisará criar este arquivo executando `pip freeze > requirements.txt` no seu ambiente ativado)
    ```sh
    pip install -r requirements.txt
    ```

---

## Como Usar

O modelo pode ser executado através do script principal na pasta `src`.

1.  **Prepare seus dados:** Certifique-se de que seus dados de contratos estão em formato `.csv` na pasta `/dados`, com as seguintes colunas: `vertice_1`, `vertice_2`, `prob_positiva`, `peso`.

2.  **Execute o modelo:**
    ```sh
    python src/main.py --data dados/run1_p1.csv --output resultados/
    ```
    O script irá gerar os resultados (a partição de clusters e as estatísticas) na pasta de saída especificada.

---

## Estrutura do Projeto

```
.
├── dados/            # Arquivos de dados de entrada (.csv)
├── src/              # Código-fonte do projeto (.py)
│   ├── construtor_grafo.py
│   ├── modelo_otimizacao.py
│   └── main.py
├── resultados/       # Arquivos de saída (tabelas, imagens)
├── venv/             # Ambiente virtual do Python
└── README.md
```

---

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo `LICENSE` para mais detalhes.

---

## Contato e Citação

Axl Silva de Andrade - [seu-email@exemplo.com]

Se você utilizar este trabalho em sua pesquisa, por favor, cite a dissertação:

> Andrade, A. S. (2026). *Análise Dinâmica de Redes de Corrupção com Equilíbrio Estrutural em Multigrafos*. Dissertação de Mestrado, Programa de Pós-Graduação em Modelagem Matemática e Computacional, Universidade Federal Rural do Rio de Janeiro, Seropédica, RJ, Brasil.