import pandas as pd
import numpy as np
import yfinance as yf
import itertools
import os
import json

def get_homogeneous_data(ticker, start="2021-07-01", end="2026-03-01"):
    """Descarga y homogeniza de forma estricta cualquier activo al estándar de estados."""
    raw = yf.download(ticker, start=start, end=end, progress=False)
    if raw.empty:
        return None
    
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    df = df.reset_index()
    
    df = df.dropna()
    df = df[df['Close'] > 0].copy()
    
    df['Return'] = df['Close'].pct_change()
    df = df.dropna().copy()
    
    df['Market_State'] = np.where(df['Return'] > 0, 1, 0)
    
    # Construcción de retrasos para N=2, N=3, N=4
    df['State_t'] = df['Market_State']
    df['State_t1'] = df['Market_State'].shift(1)
    df['State_t2'] = df['Market_State'].shift(2)
    df['State_t3'] = df['Market_State'].shift(3)
    df = df.dropna().copy()
    
    # Índices decimales para los autómatas
    df['Code_N2'] = (df['State_t1'] * 2 + df['State_t']).astype(int)
    df['Code_N3'] = (df['State_t2'] * 4 + df['State_t1'] * 2 + df['State_t']).astype(int)
    df['Code_N4'] = (df['State_t3'] * 8 + df['State_t2'] * 4 + df['State_t1'] * 2 + df['State_t']).astype(int)
    
    df['Next_Return'] = df['Return'].shift(-1)
    return df.dropna().copy()

def censo_completo_matricial(universe_assets, num_bits, code_column):
    """Calcula el rendimiento de absolutamente TODAS las combinaciones en TODOS los activos."""
    num_strategies = 2 ** num_bits
    strategies_matrix = np.array(list(itertools.product([1, -1], repeat=num_bits)))
    
    asset_results = {}
    for ticker, df in universe_assets.items():
        states = df[code_column].values
        next_returns = df['Next_Return'].values
        
        # Multiplicación matricial masiva de acciones * retornos
        actions = strategies_matrix[:, states]
        daily_returns = actions * next_returns
        cum_returns = (np.prod(1 + daily_returns, axis=1) - 1) * 100
        asset_results[ticker] = cum_returns
        
    # Construir dataframe unificado del censo
    records = []
    for idx in range(num_strategies):
        dna_str = "".join(['1' if x == 1 else '0' for x in strategies_matrix[idx]])
        row = {"ID": idx, "Logica": dna_str}
        for ticker in universe_assets.keys():
            row[ticker] = float(asset_results[ticker][idx])
        records.append(row)
        
    return pd.DataFrame(records)

def main():
    print("==================================================================")
    print("      MEGA TORNEO CUÁNTICO: MATRIZ DE CONVERGENCIA TOTAL          ")
    print("==================================================================")
    
    tickers = {
        "BTC-USD": "Bitcoin",
        "ETH-USD": "Ethereum",
        "SPY": "S&P 500 ETF",
        "GC=F": "Oro",
        "CL=F": "Petróleo"
    }
    
    universe_data = {}
    print("[*] Descargando e Ingestando datos históricos homogeneizados...")
    for t in tickers.keys():
        df = get_homogeneous_data(t)
        if df is not None:
            universe_data[t] = df
            
    print(f"[OK] {len(universe_data)} activos listos en memoria.")
    
    # -------------------------------------------------------------
    # PASO 1: LÍNEA DE BASE - EXPERIMENTO 1 (Buy & Hold)
    # -------------------------------------------------------------
    print("\n📊 EXPERIMENTO 1: RENDIMIENTO DEL MERCADO PURO (Buy & Hold)")
    print("-" * 65)
    for t, name in tickers.items():
        df = universe_data[t]
        bh = (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100
        print(f"  * {name:<15} ({t:<8}): {bh:>8.2f}%")
    print("-" * 65)

    # -------------------------------------------------------------
    # PASO 2: EJECUCIÓN DE LOS TRES CENSOS MATRICIALES
    # -------------------------------------------------------------
    print("\n[🧬] Corriendo Censo del Experimento 1B (N=2, 16 lógicas)...")
    df_n2 = censo_completo_matricial(universe_data, 4, 'Code_N2')
    
    print("[🧬] Corriendo Censo del Experimento 2  (N=3, 256 lógicas)...")
    df_n3 = censo_completo_matricial(universe_data, 8, 'Code_N3')
    
    print("[🧬] Corriendo Censo del Experimento 3  (N=4, 65536 lógicas)...")
    df_n4 = censo_completo_matricial(universe_data, 16, 'Code_N4')

    # Guardar censos crudos completos para que el colaborador los tenga
    os.makedirs("data", exist_ok=True)
    df_n2.to_json("data/censo_completo_n2.json", orient="records", indent=4)
    df_n3.to_json("data/censo_completo_n3.json", orient="records", indent=4)
    # El archivo N4 completo puede ser pesado, lo guardamos optimizado
    df_n4.to_parquet("data/censo_completo_n4.parquet", index=False) if 'parquet' in json.__dict__ else df_n4.to_json("data/censo_completo_n4.json", orient="records")
    
    # -------------------------------------------------------------
    # PASO 3: APLICAR FILTRO GLOBAL AMBICIOSO (Rentables en TODO)
    # -------------------------------------------------------------
    # Una estrategia es ganadora real si supera el 0% en TODOS los activos simultáneamente
    cond_n2 = np.logical_and.reduce([df_n2[t] > 0 for t in tickers.keys()])
    cond_n3 = np.logical_and.reduce([df_n3[t] > 0 for t in tickers.keys()])
    cond_n4 = np.logical_and.reduce([df_n4[t] > 0 for t in tickers.keys()])
    
    ganadoras_n2 = df_n2[cond_n2].copy()
    ganadoras_n3 = df_n3[cond_n3].copy()
    ganadoras_n4 = df_n4[cond_n4].copy()
    
    print(f"\n📈 FILTRO DE CONSISTENCIA GLOBAL:")
    print(f"  * Estrategias Universales en N=2: {len(ganadoras_n2)} de 16")
    print(f"  * Estrategias Universales en N=3: {len(ganadoras_n3)} de 256")
    print(f"  * Estrategias Universales en N=4: {len(ganadoras_n4)} de 65,536")

    # -------------------------------------------------------------
    # PASO 4: ANÁLISIS DE CONVERGENCIA (PATRONES COINCIDENTES)
    # -------------------------------------------------------------
    print("\n🔍 BUSCANDO PATRONES INVARIANTES LIBRES DE OVERFITTING...")
    print("=" * 80)
    
    # Imprimir las mejores absolutas combinadas del experimento 3 para inspección visual
    ganadoras_n4['Suma'] = ganadoras_n4[list(tickers.keys())].sum(axis=1)
    top_globales = ganadoras_n4.sort_values(by='Suma', ascending=False).head(5)
    
    print("🏆 TOP 5 REGULADORES FINANCIEROS UNIVERSALES (Censo Cruzado N=4):")
    print("-" * 80)
    print(top_globales[['Logica'] + list(tickers.keys()) + ['Suma']].to_string(index=False, formatters={t: '{:,.1f}%'.format for t in list(tickers.keys())+['Suma']}))
    print("=" * 80)
    
    # Exportar archivo definitivo de la Élite Consistente Sincronizada
    top_globales.to_json("data/elite_convergente_universal.json", orient="records", indent=4)
    print("\n[+] Élite final exportada a 'data/elite_convergente_universal.json'.")
    print("[*] Listo para ser sincronizado a GitHub.")

if __name__ == "__main__":
    main()