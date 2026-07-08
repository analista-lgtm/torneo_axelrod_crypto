import os
from src.downloader import download_binance_daily_data

def main():
    # Asegurar que la carpeta data exista
    os.makedirs("data", exist_ok=True)
    
    # Definir ruta de salida
    output_path = "data/btc_1d_5y.csv"
    
    # Ejecutar la descarga
    df_btc = download_binance_daily_data(
        symbol="BTCUSDT", 
        start_date="2021-07-01", 
        end_date="2026-07-01"
    )
    
    # Guardar a CSV
    df_btc.to_csv(output_path, index=False)
    print(f"Datos guardados exitosamente en: {output_path}")

if __name__ == "__main__":
    main()