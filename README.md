# Dynamic Analysis of Corruption Networks with Structural Balance on Multigraphs

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

> A multi-objective mathematical optimization model for the dynamic analysis of corruption networks, using Structural Balance theory on multigraphs.

This repository contains the code and documentation for the research developed in the Master's thesis of **Axl Silva de Andrade**, as part of the Graduate Program in Mathematical and Computational Modeling at UFRRJ. The entire development environment is containerized using Docker and VS Code Dev Containers for simple, one-click setup and perfect reproducibility.

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

This project addresses this limitation by proposing a **multi-objective optimization model** based on **Probabilistic Structural Balance** theory and **multigraphs**. The goal is to explore the trade-off between two conflicting objectives:
1.  **Minimizing Disagreement:** Finding the most mathematically consistent clusters based on the probabilistic risk of each contract.
2.  **Minimizing the Number of Clusters:** Producing simpler, more interpretable results.

This approach allows for a dynamic and nuanced analysis, identifying the evolution of *State Capture* clusters rather than just a static snapshot.

---

## Core Concepts

* **Structural Balance:** A theory from social psychology that posits that networks tend to organize into groups with internal cohesion and external hostility.
* **Correlation Clustering (CC):** An optimization problem that seeks the best partition of a graph to minimize "disagreement".
* **Multigraph:** A graph structure that allows multiple parallel edges between the same pair of vertices, ideal for modeling repeated contracts.
* **Multi-Objective Optimization:** A technique used to find a set of optimal solutions (a Pareto front) that represent the best possible trade-offs between two or more conflicting objectives.

---

## Getting Started

This project is configured to run inside a **Dev Container**, which automates the entire setup process.

### Prerequisites

* [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
* [Visual Studio Code](https://code.visualstudio.com/)
* The [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) for VS Code.
* A valid license for the Gurobi Optimizer.

### Installation

The installation is fully automated by VS Code.

1.  **Clone the repository:**
    ```sh
    git clone [https://github.com/axlandrade/dynamic-corruption-detection.git](https://github.com/axlandrade/dynamic-corruption-detection.git)
    cd dynamic-corruption-detection
    ```

2.  **Open the folder in VS Code.**

3.  **Reopen in Container:** A notification will appear in the bottom-right corner. Click on **"Reopen in Container"**.

That's it. VS Code will now build the Docker image, install all Python dependencies from `requirements.txt`, and launch a fully configured development environment.

---

## Usage

Once the Dev Container is running, all commands should be executed from the **integrated terminal in VS Code**.

1.  **Generate the Research Instances:**
    The first step is to generate the multigraph `.csv` files based on the data from Ponciano (2017).
    ```sh
    python src/instance_generator.py
    ```
    This will populate the `/data` folder with 10 files, from `run1_P1_k5.csv` to `run1_P10_k5.csv`.

2.  **Run a Single Experiment:**
    To test a single instance with a specific trade-off parameter (`lambda`), use the `main.py` script.
    ```sh
    # Example: Run instance P1 with a balance between objectives (lambda=0.5)
    python src/main.py --data data/run1_P1_k5.csv --output_dir results/run1_P1_k5_lambda_0.5 --lambda_weight 0.5
    ```

3.  **Run the Full Batch of Experiments:**
    To execute all 50 experiments (10 instances x 5 lambda values), use the provided shell script.
    ```sh
    ./run_experiments.sh
    ```
    Results for each run will be saved in a dedicated subfolder within the `/results` directory, ready for analysis.

---

## Project Structure

```
.
├── .devcontainer/    # VS Code Dev Container configuration (json, Dockerfile)
├── data/             # Input data files (.csv)
├── src/              # Python source code (.py)
├── results/          # Output files (tables, images) - Ignored by Git
|
├── .gitignore        # Specifies files for Git to ignore
├── LICENSE           # Project license (MIT)
├── README.md         # This file
├── requirements.txt  # Python package dependencies
└── run_experiments.sh # Script to run all experiments
```

---

## License

This project is licensed under the MIT License - see the `LICENSE` file for more details.

---

## Contact and Citation

Axl Silva de Andrade - [axlsandrade.ufrrj@gmail.com]

<!---If you use this work in your research, please cite the dissertation:

> Andrade, A. S. (2026). *Dynamic Analysis of Corruption Networks with Structural Balance on Multigraphs*. Master's Thesis, Graduate Program in Mathematical and Computational Modeling, Federal Rural University of Rio de Janeiro, Seropédica, RJ, Brazil.--->