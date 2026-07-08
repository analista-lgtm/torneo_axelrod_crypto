import pandas as pd
import numpy as np
import itertools
import json
import os

def run_all_experiments(data_path="data/btc_1d_5y.csv", output_dir="data"):
    print("==================================================================")
    print("   INICIANDO MOTOR QUANT TOURNAMENT - EXPERIMENTOS 2 Y 3")
    print("==================================================================")
    
    # 1. Cargar y preparar datos base
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df['Return'] = df['Close'].pct_change()
    df['Market_State'] = np.where(df['Return'] > 0, 1, 0)
    
    # Columnas de memoria para N=3 y N=4
    df['State_t'] = df['Market_State']
    df['State_t1'] = df['Market_State'].shift(1)
    df['State_t2'] = df['Market_State'].shift(2)
    df['State_t3'] = df['Market_State'].shift(3)
    df = df.dropna().copy()
    
    # Códigos de estado decimales
    df['State_Code_N3'] = (df['State_t2'] * 4 + df['State_t1'] * 2 + df['State_t']).astype(int)
    df['State_Code_N4'] = (df['State_t3'] * 8 + df['State_t2'] * 4 + df['State_t1'] * 2 + df['State_t']).astype(int)
    
    df['Next_Return'] = df['Return'].shift(-1)
    df = df.dropna().copy()
    
    df['Month'] = df['Date'].dt.strftime('%Y-%m')
    meses_unicos = df['Month'].unique().tolist()
    
    # Benchmark Buy & Hold
    df['B&H_Equity'] = (1 + df['Next_Return']).cumprod()
    bh_monthly = df.groupby('Month')['B&H_Equity'].last().tolist()
    
    # Definición de la matriz de ejecución de experimentos
    configs = {
        "2a": {"name": "Clásico 2A (N=3, Long/Cash)", "bits": 8, "state_col": "State_Code_N3", "short_val": 0},
        "2b": {"name": "Clásico 2B (N=3, Long/Short)", "bits": 8, "state_col": "State_Code_N3", "short_val": -1},
        "3a": {"name": "Expandido 3A (N=4, Long/Cash)", "bits": 16, "state_col": "State_Code_N4", "short_val": 0},
        "3b": {"name": "Expandido 3B (N=4, Long/Short)", "bits": 16, "state_col": "State_Code_N4", "short_val": -1},
    }
    
    os.makedirs(output_dir, exist_ok=True)
    
    for exp_id, cfg in configs.items():
        print(f"\nProcesando {cfg['name']}...")
        print(f"Generando universo de {2**cfg['bits']} estrategias...")
        strategies = list(itertools.product([0, 1], repeat=cfg['bits']))
        
        metrics = []
        all_equities_temp = {}
        
        # Simulación vectorizada
        for idx, strat in enumerate(strategies):
            actions = df[cfg['state_col']].map(lambda x: 1 if strat[x] == 1 else cfg['short_val'])
            strat_returns = actions * df['Next_Return']
            equity_curve = (1 + strat_returns).cumprod()
            
            total_return = equity_curve.iloc[-1] - 1
            std_dev = strat_returns.std()
            sharpe = (np.sqrt(365) * strat_returns.mean() / std_dev) if std_dev > 0 else 0
            
            roll_max = equity_curve.cummax()
            drawdowns = (equity_curve / roll_max) - 1
            max_dd = drawdowns.min()
            
            strat_name = f"Strat_{idx}"
            logic_str = ''.join(map(str, strat))
            
            metrics.append({
                "Estrategia": strat_name,
                "Logica": logic_str,
                "Retorno": round(total_return * 100, 2),
                "Sharpe": round(sharpe, 2),
                "Max_DD": round(max_dd * 100, 2)
            })
            
            # Guardar temporalmente las agrupaciones mensuales
            df['Temp_Equity'] = equity_curve
            all_equities_temp[strat_name] = df.groupby('Month')['Temp_Equity'].last().tolist()
            
        # --- TRUCO DE OPTIMIZACIÓN DE RENDIMIENTO ---
        # Ordenamos las estrategias por retorno para filtrar extremos antes de exportar curvas de capital
        metrics_sorted = sorted(metrics, key=lambda x: x['Retorno'], reverse=True)
        top_keys = [m['Estrategia'] for m in metrics_sorted[:10]]
        bottom_keys = [m['Estrategia'] for m in metrics_sorted[-10:]]
        
        # Filtramos el diccionario guardando solo lo necesario para el gráfico
        filtered_equities = {"Buy_and_Hold": bh_monthly}
        for k in top_keys + bottom_keys:
            filtered_equities[k] = all_equities_temp[k]
            
        # Guardar en disco de forma segura e independiente
        with open(f"{output_dir}/metrics_{exp_id}.json", "w") as f:
            json.dump(metrics, f)
        with open(f"{output_dir}/equity_{exp_id}.json", "w") as f:
            json.dump({"labels": meses_unicos, "datasets": filtered_equities}, f)
            
        print(f"-> ¡Éxito! Archivos guardados: metrics_{exp_id}.json y equity_{exp_id}.json")

    print("\n==================================================================")
    print("   SIMULACIÓN FINALIZADA - TODOS LOS EXPERIMENTOS ASEGURADOS")
    print("==================================================================")

if __name__ == "__main__":
    run_all_experiments()