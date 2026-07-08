import requests
import pandas as pd
import time
from datetime import datetime

def download_binance_daily_data(symbol="BTCUSDT", start_date="2021-07-01", end_date="2026-07-01"):
    """
    Descarga el historial de velas diarias de Binance manejando la paginación de la API.
    """
    url = "https://api.binance.com/api/v3/klines"
    
    # Convertir fechas a timestamps de milisegundos requeridos por Binance
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
    
    all_candles = []
    current_start = start_ts
    
    print(f"Iniciando descarga de {symbol} desde {start_date} hasta {end_date}...")
    
    while current_start < end_ts:
        params = {
            "symbol": symbol,
            "interval": "1d",
            "startTime": current_start,
            "endTime": end_ts,
            "limit": 1000
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            print(f"Error en la API de Binance: {response.status_code}")
            break
            
        data = response.json()
        
        if not data:
            break
            
        all_candles.extend(data)
        
        # El nuevo startTime será el timestamp de la última vela recibida + 1 día (en ms)
        last_candle_ts = data[-1][0]
        current_start = last_candle_ts + (24 * 60 * 60 * 1000)
        
        print(f"Descargadas {len(data)} velas. Avanzando en la línea de tiempo...")
        time.sleep(0.5) # Respetar límites de rate de la API
        
    # Procesar los datos a un DataFrame de Pandas
    # Columnas según API de Binance: 0=OpenTime, 1=Open, 2=High, 3=Low, 4=Close, 5=Volume...
    df = pd.DataFrame(all_candles)
    df = df[[0, 1, 2, 3, 4, 5]]
    df.columns = ["Timestamp", "Open", "High", "Low", "Close", "Volume"]
    
    # Formatear tipos de datos
    df["Date"] = pd.to_datetime(df["Timestamp"], unit="ms").dt.date
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = df[col].astype(float)
        
    # Reordenar y limpiar
    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]
    
    print(f"Descarga completada. Total registros: {len(df)}")
    return df