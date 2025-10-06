# src/create_real_network.py

import pandas as pd
import os


def calculate_risk_score(row: pd.Series) -> float:
    """
    [English]
    Calculates a heuristic corruption risk score for a contract (a DataFrame row).
    The score starts at a base of 0.5 and increases based on risk indicators.

    [Português]
    Calcula um score heurístico de risco de corrupção para um contrato (uma linha do DataFrame).
    O score parte de uma base de 0.5 e aumenta com base em indicadores de risco.
    """
    score = 0.5  # Base risk / Risco base

    # --- Rule 1: High-risk procurement modalities ---
    # [Português] Modalidades sem competição ampla aumentam o risco.
    if isinstance(row['modalidadeCompra'], str):
        modalidade = row['modalidadeCompra'].upper()
        if "DISPENSA DE LICITAÇÃO" in modalidade or "INEXIGIBILIDADE" in modalidade:
            score += 0.3

    # --- Rule 2: Contract value amendments ---
    # [Português] Aumentos significativos no valor do contrato podem indicar aditivos suspeitos.
    valor_inicial = row['valorInicialCompra']
    valor_final = row['valorFinalCompra']
    # More than 20% increase
    if valor_inicial > 0 and valor_final > (valor_inicial * 1.2):
        score += 0.15

    # --- Rule 3: Contract situation ---
    # [Português] Contratos rescindidos podem indicar problemas na execução.
    if isinstance(row['situacaoContrato'], str):
        if "RESCINDIDO" in row['situacaoContrato'].upper():
            score += 0.1

    # [English] Clip the score to ensure it's between 0.0 and 1.0.
    # [Português] Garante que o score final permaneça no intervalo [0, 1].
    return min(score, 1.0)


def main():
    """
    [English]
    Main function to process the enriched real-world data and generate the
    final network input file for the optimization models.

    [Português]
    Função principal para processar os dados reais enriquecidos e gerar o
    arquivo de entrada da rede final para os modelos de otimização.
    """
    # --- Configuration ---
    input_dir = 'data'
    input_filename = 'contratos_enriquecidos.csv'
    output_filename = 'rede_real_input.csv'

    input_path = os.path.join(input_dir, input_filename)
    output_path = os.path.join(input_dir, output_filename)

    print(f"--- Iniciando a criação da rede com dados reais ---")
    print(f"Lendo dados de: {input_path}")

    # --- 1. Load Data ---
    try:
        # Using low_memory=False to handle the DtypeWarning you saw before
        df = pd.read_csv(input_path, low_memory=False)
        print(f"Sucesso! {len(df)} contratos carregados.")
    except FileNotFoundError:
        print(
            f"ERRO: Arquivo '{input_path}' não encontrado. Certifique-se de que ele está na pasta 'data'.")
        return

    # --- 2. Calculate Risk Score (positive_prob) ---
    print("Calculando o score de risco para cada contrato...")
    df['positive_prob'] = df.apply(calculate_risk_score, axis=1)
    print("Cálculo do risco finalizado.")

    # --- 3. Build the Final Network DataFrame ---
    print("Montando o arquivo de rede final...")
    df_network = pd.DataFrame()
    df_network['node_1'] = df['unidadeGestora_nome']
    df_network['node_2'] = df['fornecedor_cnpjFormatado']
    df_network['positive_prob'] = df['positive_prob']
    df_network['weight'] = 1.0  # Default weight

    # --- 4. Clean and Save ---
    # [English] Remove rows where either the agency or the supplier is not defined.
    # [Português] Remove linhas onde o órgão ou o fornecedor não estão definidos.
    initial_rows = len(df_network)
    df_network.dropna(subset=['node_1', 'node_2'], inplace=True)
    final_rows = len(df_network)
    print(f"{initial_rows - final_rows} contratos removidos por falta de informação de 'órgão' ou 'fornecedor'.")

    df_network.to_csv(output_path, index=False)
    print(f"\nSUCESSO! Arquivo de rede final salvo em: '{output_path}'")
    print(
        f"O arquivo contém {final_rows} arestas (contratos) e está pronto para ser usado.")


if __name__ == '__main__':
    main()
