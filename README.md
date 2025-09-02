# Dynamic Analysis of Corruption Networks with Structural Balance on Multigraphs

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

> A mathematical optimization model for the dynamic analysis of corruption networks, using Structural Balance theory on multigraphs.

This repository contains the code and documentation for the research developed in the Master's thesis of **Axl Silva de Andrade**, as part of the Graduate Program in Mathematical and Computational Modeling at UFRRJ.

---

## Table of Contents

- [About the Project](#about-the-project)
- [Core Concepts](#core-concepts)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [License](#license)
- [Contact and Citation](#contact-and-citation)

---

## About the Project

Detecting corruption in public procurement is a complex challenge. Models based on simple graphs, which represent the relationship between two entities with a single edge, lose valuable information about the dynamics and frequency of contractual interactions.

This project proposes an extension of the **Probabilistic Structural Balance** model to **multigraphs**, allowing for a more faithful representation of procurement networks where multiple contracts between the same entities are common. The objective is to develop an AI model, based on mathematical optimization, capable of identifying dynamic patterns and the evolution of *State Capture* clusters.

---

## Core Concepts

* **Structural Balance:** A theory from social psychology that posits that networks tend to organize into groups with internal cohesion and external hostility.
* **Correlation Clustering (CC):** An optimization problem that seeks the best partition of a graph to minimize "disagreement" (positive edges between clusters and negative edges within clusters).
* **Multigraph:** A graph structure that allows multiple parallel edges between the same pair of vertices, ideal for modeling repeated contracts.

---

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine.

### Prerequisites

* Python 3.9+
* An optimization solver, such as Gurobi or CPLEX, installed and with a valid license.

### Installation

1.  **Clone the repository:**
    ```sh
    git clone [https://github.com/axlandrade/dynamic-corruption-detection.git](https://github.com/axlandrade/dynamic-corruption-detection.git)
    cd dynamic-corruption-detection
    ```

2.  **Create and activate a virtual environment:**
    ```sh
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On Linux/Mac:
    source venv/bin/activate
    ```

3.  **Install the dependencies:**
    (You will need to create this file by running `pip freeze > requirements.txt` in your activated environment)
    ```sh
    pip install -r requirements.txt
    ```

---

## Usage

The model can be executed through the main script in the `src` folder.

1.  **Prepare your data:** Ensure your contract data is in `.csv` format within the `/data` folder, with the following columns: `node_1`, `node_2`, `positive_prob`, `weight`.

2.  **Run the model:**
    ```sh
    python src/main.py --data data/run1_p1.csv --output_dir results/
    ```
    The script will generate the results (the cluster partition and statistics) in the specified output directory.

---

## Project Structure

```
.
├── data/             # Input data files (.csv)
├── src/              # Project source code (.py)
│   ├── graph_constructor.py
│   ├── optimization_model.py
│   └── main.py
├── results/          # Output files (tables, images)
├── venv/             # Python virtual environment
└── README.md
```

---

## License

This project is licensed under the MIT License - see the `LICENSE` file for more details.

---

## Contact and Citation

Axl Silva de Andrade - [axlsandrade.ufrrj@gmail.com]

If you use this work in your research, please cite the dissertation:

> Andrade, A. S. (2026). *Análise Dinâmica de Redes de Corrupção com Equilíbrio Estrutural em Multigrafos*. Master's Thesis, Graduate Program in Mathematical and Computational Modeling, Federal Rural University of Rio de Janeiro, Seropédica, RJ, Brazil.