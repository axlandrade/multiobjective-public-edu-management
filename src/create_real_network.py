# src/create_real_network.py

import pandas as pd
import os

def calculate_risk_score(row: pd.Series) -> float:
    """
    Calcula a probabilidade de risco (0.1 a 0.95) baseada em 'Red Flags'.
    Metodologia baseada em Fazekas et al. (2013) e Ponciano (2017).
    """
    # 1. Risco Base (Incerteza inerente/Máxima Entropia)
    risk_score = 0.5
    
    # --- ANÁLISE DA COMPETITIVIDADE (Peso Alto) ---
    # Converte para string e maiúscula para evitar erros de tipo
    modalidade = str(row.get('modalidadeCompra', '')).upper()
    
    # Dispensa e Inexigibilidade: Baixíssima competição
    if "DISPENSA" in modalidade or "INEXIGIBILIDADE" in modalidade:
        risk_score += 0.25
    # Convite: Competição restrita
    elif "CONVITE" in modalidade:
        risk_score += 0.15
    # Pregão/Concorrência: Alta competição teórica (Mitigador)
    elif "PREGÃO" in modalidade or "CONCORRÊNCIA" in modalidade:
        risk_score -= 0.10

    # --- ANÁLISE FINANCEIRA (Sobrepreço/Aditivos) ---
    try:
        valor_inicial = float(row.get('valorInicialCompra', 0) or 0)
        valor_final = float(row.get('valorFinalCompra', 0) or 0)
        
        if valor_inicial > 0:
            ratio = valor_final / valor_inicial
            # Aditivos acima de 25% (limite legal geral) são forte indício
            if ratio > 1.25:
                risk_score += 0.20
            elif ratio > 1.0: # Algum aditivo
                risk_score += 0.05
                
        # --- ANÁLISE DE ANOMALIAS CADASTRAIS (Lei de Benford Simplificada) ---
        # Valores "Redondos" (ex: 150.000,00) são estatisticamente raros em contabilidade honesta
        if valor_final > 1000 and valor_final % 1000 == 0:
            risk_score += 0.10
            
    except (ValueError, TypeError):
        pass # Ignora erros de conversão numérica

    # --- ANÁLISE DE EXECUÇÃO ---
    situacao = str(row.get('situacaoContrato', '')).upper()
    if "RESCINDIDO" in situacao or "ANULADO" in situacao:
        risk_score += 0.15

    # --- NORMALIZAÇÃO ---
    # Garante que a probabilidade fique entre [0.1, 0.95]
    return max(0.1, min(risk_score, 0.95))

def process_and_save_network(input_path: str, output_path: str) -> int:
    """
    Processa os dados brutos e salva o arquivo de rede com probabilidades.
    Retorna o número de arestas (contratos) processados.
    """
    print(f"--- Iniciando a criação da rede com dados reais ---")
    print(f"Lendo dados de: {input_path}")
    
    try:
        # low_memory=False ajuda com arquivos grandes que têm tipos mistos
        df = pd.read_csv(input_path, low_memory=False)
    except FileNotFoundError:
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")
    except Exception as e:
        raise Exception(f"Erro ao ler CSV: {e}")

    print(f"Sucesso! {len(df)} contratos carregados.")

    print("Calculando o score de risco para cada contrato...")
    # Aplica a função de risco linha a linha
    df['positive_prob'] = df.apply(calculate_risk_score, axis=1)

    # Cria o dataframe final da rede
    df_network = pd.DataFrame({
        'node_1': df['unidadeGestora_nome'],
        'node_2': df['fornecedor_cnpjFormatado'],
        'positive_prob': df['positive_prob'],
        'weight': 1.0 # Peso padrão 1.0, mas poderia ser o valor do contrato normalizado
    })
    
    # Remove linhas onde algum nó é nulo/vazio
    df_network.dropna(subset=['node_1', 'node_2'], inplace=True)
    final_rows = len(df_network)

    # Cria diretório se não existir
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    df_network.to_csv(output_path, index=False)
    print(f"\nSUCESSO! Arquivo de rede final salvo em: '{output_path}' com {final_rows} arestas.")
    
    return final_rows

# Bloco para teste direto via terminal (opcional)
if __name__ == '__main__':
    try:
        process_and_save_network('data/contratos_enriquecidos.csv', 'data/rede_real_input.csv')
    except Exception as e:
        print(f"Erro: {e}")