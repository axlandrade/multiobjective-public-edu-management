# Dynamic Analysis of Corruption Networks with Structural Balance on Multigraphs

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

> A mathematical optimization model for the dynamic analysis of corruption networks, using Structural Balance theory on multigraphs.

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

This project proposes an extension of the **Probabilistic Structural Balance** model to **multigraphs**, allowing for a more faithful representation of procurement networks where multiple contracts between the same entities are common. The objective is to develop an AI model, based on mathematical optimization, capable of identifying dynamic patterns and the evolution of *State Capture* clusters.

---

## Core Concepts

* **Structural Balance:** A theory from social psychology that posits that networks tend to organize into groups with internal cohesion and external hostility.
* **Correlation Clustering (CC):** An optimization problem that seeks the best partition of a graph to minimize "disagreement" (positive edges between clusters and negative edges within clusters).
* **Multigraph:** A graph structure that allows multiple parallel edges between the same pair of vertices, ideal for modeling repeated contracts.

---

## Getting Started

This project is configured to run inside a **Dev Container**, which automates the entire setup process.

### Prerequisites

* [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
* [Visual Studio Code](https://code.visualstudio.com/)
* The [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) for VS Code.
* A valid license for an optimization solver (e.g., Gurobi). You will need to configure Gurobi license access within the container environment if required.

### Installation

The installation is fully automated by VS Code.

1.  **Clone the repository:**
    ```sh
    git clone [https://github.com/axlandrade/dynamic-corruption-detection.git](https://github.com/axlandrade/dynamic-corruption-detection.git)
    cd dynamic-corruption-detection
    ```

2.  **Open the folder in VS Code.**

3.  **Reopen in Container:** A notification will appear in the bottom-right corner. Click on **"Reopen in Container"**.

That's it. VS Code will now build the Docker image, install all Python dependencies, configure the extensions (like GitLens and Jupyter), and launch a fully configured development environment.

---

## Usage

Once the Dev Container is running, all commands should be executed from the **integrated terminal in VS Code**.

1.  **Generate the research instances:**
    The first step is to generate the multigraph `.csv` files from the base data.
    ```sh
    python src/instance_generator.py
    ```
    This will populate the `/data` folder with the `run1_P1_k5.csv`, `run1_P2_k5.csv`, etc. files.

2.  **Run a single experiment:**
    To test a single instance, use the `main.py` script.
    ```sh
    python src/main.py --data data/run1_P1_k5.csv --output_dir results/run1_P1_k5_results
    ```

3.  **Run the full batch of experiments:**
    To execute all 10 experiments in sequence, use the provided shell script.
    ```sh
    ./run_experiments.sh
    ```
    Results for each run will be saved in a dedicated subfolder within the `/results` directory.

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

If you use this work in your research, please cite the dissertation:

> Andrade, A. S. (2026). *Dynamic Analysis of Corruption Networks with Structural Balance on Multigraphs*. Master's Thesis, Graduate Program in Mathematical and Computational Modeling, Federal Rural University of Rio de Janeiro, Seropédica, RJ, Brazil.