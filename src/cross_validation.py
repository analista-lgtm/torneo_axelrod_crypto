import pandas as pd
import numpy as np
import json
import os

import yfinance as yf

def safe_data_ingestion(ticker, start_date="2021-07-01", end_date="2026-03-01"):
    """
    Capa de Validación y Saneamiento de Datos (Data Cleansing Layer).
    Garantiza que cualquier fuente de Yahoo Finance replique la estructura limpia de Binance.
    """
    print(f"\n[INGESTA] Descargando {ticker} desde Yahoo Finance...")
    raw_data = yf.download(ticker, start=start_date, end=end_date, progress=False)
    
    if raw_data.empty:
        print(f"[-] ERROR CRÍTICO: No se encontraron datos para {ticker}. Saltando activo.")
        return None
    
    # 1. Desarmar índices multinivel de Yahoo Finance si existen
    df = raw_data.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    
    df = df.reset_index()
    
    # 2. Renombrar y validar columnas esenciales
    if 'Close' not in df.columns:
        # Intentar con Adj Close si Close no está explícito
        if 'Adj Close' in df.columns:
            df['Close'] = df['Adj Close']
        else:
            print(f"[-] ERROR: Estructura de datos inválida para {ticker}. Saltando.")
            return None
            
    df = df[['Date', 'Close']].copy()
    
    # 3. Limpieza de anomalías (Valores nulos, ceros o infinitos por cierres de mercado)
    df = df.dropna()
    df = df[(df['Close'] > 0) & (np.isfinite(df['Close']))]
    
    # 4. Auditoría de consistencia de la serie de tiempo
    total_filas = len(df)
    if total_filas < 100:
        print(f"[-] ALERTA: Muestra demasiado pequeña ({total_filas} velas) para {ticker}. Saltando.")
        return None
        
    # 5. Transformación a Espacio de Estados Axelrod (N=4)
    df['Return'] = df['Close'].pct_change()
    df = df.dropna().copy()
    
    df['Market_State'] = np.where(df['Return'] > 0, 1, 0)
    df['State_t'] = df['Market_State']
    df['State_t1'] = df['Market_State'].shift(1)
    df['State_t2'] = df['Market_State'].shift(2)
    df['State_t3'] = df['Market_State'].shift(3)
    df = df.dropna().copy()
    
    # Cálculo decimal del código binario de 4 días
    df['State_Code_N4'] = (df['State_t3'] * 8 + df['State_t2'] * 4 + df['State_t1'] * 2 + df['State_t']).astype(int)
    df['Next_Return'] = df['Return'].shift(-1)
    df = df.dropna().copy()
    
    print(f"[OK] {ticker} verificado con éxito. {len(df)} velas diarias saneadas listas para backtest.")
    return df

def run_backtest(df, logic_str, asset_type="traditional"):
    """
    Ejecución vectorizada del ADN de la estrategia sobre la serie temporal saneada.
    """
    # Determinar factor de anualización óptimo según la densidad del mercado
    # Cripto opera ~365 días; Acciones/Commodities/Divisas operan ~252 días hábiles
    ann_factor = 365 if asset_type == "crypto" else 252
    
    strat_dna = [int(bit) for bit in logic_str]
    # Mapear acciones: 1 (Long), -1 (Short en modo agresivo)
    actions = df['State_Code_N4'].map(lambda x: 1 if strat_dna[x] == 1 else -1)
    
    strat_returns = actions * df['Next_Return']
    equity_curve = (1 + strat_returns).cumprod()
    
    total_return = (equity_curve.iloc[-1] - 1) * 100
    std_dev = strat_returns.std()
    sharpe = (np.sqrt(ann_factor) * strat_returns.mean() / std_dev) if std_dev > 0 else 0
    
    roll_max = equity_curve.cummax()
    drawdowns = (equity_curve / roll_max) - 1
    max_dd = drawdowns.min() * 100
    
    return total_return, sharpe, max_dd

def main():
    print("==================================================================")
    print("   LABORATORIO QUANT: BANCO DE PRUEBAS MULTI-MERCADO (N=4)        ")
    print("==================================================================")
    
    # 1. Cargar las campeonas mutantes del experimento de Bitcoin
    btc_path = "data/metrics_3b.json"
    if not os.path.exists(btc_path):
        print(f"[-] No se encontró {btc_path}. Por favor ejecuta src/tournament.py primero.")
        return
        
    with open(btc_path, "r") as f:
        btc_metrics = json.load(f)
    
    top_btc = sorted(btc_metrics, key=lambda x: x['Retorno'], reverse=True)[:3]
    
    # 2. Definición del portafolio global de validación cruzada solicitado
    macro_universe = {
        "ETH-USD": {"desc": "Ethereum (Cripto - Alta Correlación)", "type": "crypto"},
        "SPY": {"desc": "S&P 500 ETF (Renta Variable - Tradicional)", "type": "traditional"},
        "GC=F": {"desc": "Futuros de Oro (Metales / Refugio)", "type": "traditional"},
        "CL=F": {"desc": "Futuros Petróleo Crudo (Energía / Commodity)", "type": "traditional"},
        "DX-Y.NYB": {"desc": "Índice Dólar DXY (Macro / Divisas)", "type": "traditional"}
    }
    
    # 3. Ciclo Global de Stress-Testing
    for ticker, info in macro_universe.items():
        df_clean = safe_data_ingestion(ticker)
        if df_clean is None:
            continue
            
        # Calcular rendimiento pasivo (Buy & Hold) como línea base del activo
        bh_ret = (df_clean['Close'].iloc[-1] / df_clean['Close'].iloc[0] - 1) * 100
        
        print(f"\n📈 Veredicto de Robustez para: {info['desc']}")
        print(f"--> Rendimiento del Mercado Puro (Buy & Hold): {bh_ret:.2f}%")
        print("-" * 80)
        print(f"{'Estrategia':<12} | {'Retorno BTC':<13} | {'Retorno Activo':<16} | {'Sharpe':<8} | {'Max DD':<10}")
        print("-" * 80)
        
        for champion in top_btc:
            name = champion['Estrategia']
            logic = champion['Logica']
            btc_ret = champion['Retorno']
            
            ret, sharpe, dd = run_backtest(df_clean, logic, asset_type=info['type'])
            print(f"{name:<12} | {btc_ret:>11}% | {ret:>14.2f}% | {sharpe:>8.2f} | {dd:>9.2f}%")
        print("-" * 80)

if __name__ == "__main__":
    main()