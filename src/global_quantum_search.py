import pandas as pd
import numpy as np
import yfinance as yf
import itertools
import os

def get_homogeneous_data(ticker, start="2021-07-01", end="2026-03-01"):
    """Descarga y homogeniza de forma estricta cualquier activo al estándar de estados."""
    raw = yf.download(ticker, start=start, end=end, progress=False)
    if raw.empty:
        return None
    
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    df = df.reset_index()
    
    # Saneamiento estricto: eliminar ceros y nulos divisorios
    df = df.dropna()
    df = df[df['Close'] > 0].copy()
    
    df['Return'] = df['Close'].pct_change()
    df = df.dropna().copy()
    
    df['Market_State'] = np.where(df['Return'] > 0, 1, 0)
    
    # Matrices de transiciones limpias
    df['State_t'] = df['Market_State']
    df['State_t1'] = df['Market_State'].shift(1)
    df['State_t2'] = df['Market_State'].shift(2)
    df['State_t3'] = df['Market_State'].shift(3)
    df = df.dropna().copy()
    
    # Códigos para Experimento 2 (N=3) y Experimento 3 (N=4)
    df['Code_N3'] = (df['State_t2'] * 4 + df['State_t1'] * 2 + df['State_t']).astype(int)
    df['Code_N4'] = (df['State_t3'] * 8 + df['State_t2'] * 4 + df['State_t1'] * 2 + df['State_t']).astype(int)
    
    df['Next_Return'] = df['Return'].shift(-1)
    return df.dropna().copy()

def run_matrix_tournament(universe_assets, num_states, code_column):
    """Ejecuta por fuerza bruta matricial todo el universo de estrategias en milisegundos."""
    num_strategies = 2 ** num_states
    print(f"\n[*] Generando matriz de ADN para {num_strategies} estrategias...")
    
    # Crear matriz de estrategias de tamaño (65536, 16) o (256, 8)
    # Reemplazamos el bit 0 por -1 para simular la estrategia Long/Short agresiva
    strategies_matrix = np.array(list(itertools.product([1, -1], repeat=num_states)))
    
    # Diccionario para guardar curvas de rendimiento por activo
    asset_results = {}
    
    for ticker, df in universe_assets.items():
        states = df[code_column].values
        next_returns = df['Next_Return'].values
        
        # MAGIA MATRICIAL (Advanced Indexing): Evaluamos todas las estrategias a la vez
        # actions mapea la decisión de cada estrategia para cada día: forma (num_strategies, num_days)
        actions = strategies_matrix[:, states]
        
        # Calcular retornos diarios de las 65k estrategias en este activo
        daily_returns = actions * next_returns
        
        # Rendimiento compuesto acumulado por estrategia: forma (num_strategies,)
        cum_returns = np.prod(1 + daily_returns, axis=1) - 1
        asset_results[ticker] = cum_returns * 100 # Guardar en porcentaje

    # Buscar las estrategias "Globales" (Consistentes)
    # Criterio: Deben ser rentables (Retorno > 0) en TODOS los mercados analizados
    conditions = [asset_results[ticker] > 0 for ticker in universe_assets.keys()]
    global_winners_mask = np.logical_and.reduce(conditions)
    
    indices_ganadores = np.where(global_winners_mask)[0]
    
    print(f"[FILTRO] ¡Se encontraron {len(indices_ganadores)} estrategias consistentes en TODO el portafolio global!")
    
    # Construir reporte de las mejores
    report_data = []
    for idx in indices_ganadores:
        dna_str = "".join(['1' if x == 1 else '0' for x in strategies_matrix[idx]])
        row = {"ID": idx, "Logica": dna_str}
        total_score = 0
        for ticker in universe_assets.keys():
            ret = asset_results[ticker][idx]
            row[ticker] = ret
            total_score += ret
        row["Suma_Retornos"] = total_score
        report_data.append(row)
        
    df_report = pd.DataFrame(report_data)
    if not df_report.empty:
        return df_report.sort_values(by="Suma_Retornos", ascending=False).head(10)
    return None

def main():
    print("==================================================================")
    print("   MOTOR DE BÚSQUEDA MATRICIAL GLOBAL ANTI-SESGO DE SELECCIÓN     ")
    print("==================================================================")
    
    tickers = {
        "BTC-USD": "Bitcoin",
        "ETH-USD": "Ethereum",
        "SPY": "S&P 500 ETF",
        "GC=F": "Oro",
        "CL=F": "Petróleo"
    }
    
    universe_data = {}
    for t, name in tickers.items():
        df = get_homogeneous_data(t)
        if df is not None:
            universe_data[t] = df
            
    print(f"\n[+] Datos homogeneizados correctamente para {len(universe_data)} activos.")
    
    # -------------------------------------------------------------
    # TEST 1: EXPERIMENTO 2 (N=3, 256 Estrategias)
    # -------------------------------------------------------------
    print("\n" + "="*70)
    print(" ANALIZANDO EL UNIVERSO DE LA MEMORIA DE 3 DÍAS (256 ESTRATEGIAS) ")
    print("="*70)
    top_exp2 = run_matrix_tournament(universe_data, num_states=8, code_column='Code_N3')
    if top_exp2 is not None:
        print("\n🏆 TOP 5 ESTRATEGIAS GLOBALES - EXPERIMENTO 2:")
        print(top_exp2.head(5).to_string(index=False, formatters={t: '{:,.2f}%'.format for t in tickers.keys()}))
    
    # -------------------------------------------------------------
    # TEST 2: EXPERIMENTO 3 (N=4, 65,536 Estrategias)
    # -------------------------------------------------------------
    print("\n" + "="*70)
    print(" ANALIZANDO EL UNIVERSO DE LA MEMORIA DE 4 DÍAS (65,536 ESTRATEGIAS) ")
    print("="*70)
    top_exp3 = run_matrix_tournament(universe_data, num_states=16, code_column='Code_N4')
    if top_exp3 is not None:
        print("\n🏆 TOP 5 ESTRATEGIAS GLOBALES - EXPERIMENTO 3:")
        print(top_exp3.head(5).to_string(index=False, formatters={t: '{:,.2f}%'.format for t in tickers.keys()}))

if __name__ == "__main__":
    main()