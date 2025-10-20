# src/create_real_network.py

import pandas as pd
import os

def calculate_risk_score(row: pd.Series) -> float:
    # (Esta função permanece sem alterações)
    score = 0.5
    if isinstance(row.get('modalidadeCompra'), str):
        modalidade = row['modalidadeCompra'].upper()
        if "DISPENSA DE LICITAÇÃO" in modalidade or "INEXIGIBILIDADE" in modalidade:
            score += 0.3
    valor_inicial = row.get('valorInicialCompra', 0)
    valor_final = row.get('valorFinalCompra', 0)
    if valor_inicial > 0 and valor_final > (valor_inicial * 1.2):
        score += 0.15
    if isinstance(row.get('situacaoContrato'), str):
        if "RESCINDIDO" in row['situacaoContrato'].upper():
            score += 0.1
    return min(score, 1.0)

def process_and_save_network(input_path: str, output_path: str) -> int:
    """
    Função refatorada que processa os dados brutos e salva o arquivo de rede.
    Retorna o número de arestas (contratos) processados.
    """
    print(f"--- Iniciando a criação da rede com dados reais ---")
    print(f"Lendo dados de: {input_path}")
    df = pd.read_csv(input_path, low_memory=False)
    print(f"Sucesso! {len(df)} contratos carregados.")

    print("Calculando o score de risco para cada contrato...")
    df['positive_prob'] = df.apply(calculate_risk_score, axis=1)

    df_network = pd.DataFrame({
        'node_1': df['unidadeGestora_nome'],
        'node_2': df['fornecedor_cnpjFormatado'],
        'positive_prob': df['positive_prob'],
        'weight': 1.0
    })
    
    df_network.dropna(subset=['node_1', 'node_2'], inplace=True)
    final_rows = len(df_network)

    df_network.to_csv(output_path, index=False)
    print(f"\nSUCESSO! Arquivo de rede final salvo em: '{output_path}' com {final_rows} arestas.")
    return final_rows

def main():
    # A função main agora simplesmente chama a lógica refatorada com caminhos padrão
    input_dir = 'data'
    input_filename = 'contratos_enriquecidos.csv'
    output_filename = 'rede_real_input.csv'
    input_path = os.path.join(input_dir, input_filename)
    output_path = os.path.join(input_dir, output_filename)
    
    try:
        process_and_save_network(input_path, output_path)
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{input_path}' não encontrado.")

if __name__ == '__main__':
    main()