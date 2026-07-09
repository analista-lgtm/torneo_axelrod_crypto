"""
Capa estándar de ingesta y transformación de datos multi-activo.

Todos los activos pasan por exactamente la misma tubería (misma fuente,
misma ventana temporal, misma limpieza y misma codificación de estados)
para garantizar que los resultados entre mercados sean comparables y
libres de sesgos de preparación de datos.

Convenciones del proyecto:
- Market_State: 1 si el retorno diario > 0, si no 0.
- Code_N{k}: lectura decimal de la secuencia binaria de los últimos k días,
  con el día más reciente como bit menos significativo.
- Cada activo conserva su propio calendario de negociación (cripto opera
  ~365 días/año, los mercados tradicionales ~252). La comparabilidad se
  logra con la misma ventana temporal y factores de anualización por tipo.
"""
import time

import numpy as np
import pandas as pd
import yfinance as yf

# Ventana única de análisis para todos los activos
VENTANA_INICIO = "2021-07-01"
VENTANA_FIN = "2026-07-01"

# Mínimo de velas saneadas para aceptar un activo en el torneo
MIN_VELAS = 800

# Universo de activos del laboratorio
ACTIVOS = {
    "BTC-USD": {"nombre": "Bitcoin", "tipo": "crypto"},
    "ETH-USD": {"nombre": "Ethereum", "tipo": "crypto"},
    "SPY": {"nombre": "S&P 500 ETF", "tipo": "tradicional"},
    "GC=F": {"nombre": "Oro (Futuros)", "tipo": "tradicional"},
    "CL=F": {"nombre": "Petróleo WTI (Futuros)", "tipo": "tradicional"},
    "DX-Y.NYB": {"nombre": "Índice Dólar (DXY)", "tipo": "tradicional"},
}

# Factor de anualización del Sharpe Ratio según densidad del calendario
FACTORES_ANUALIZACION = {"crypto": 365, "tradicional": 252}


def descargar_activo(ticker, inicio=VENTANA_INICIO, fin=VENTANA_FIN, reintentos=3):
    """Descarga velas diarias desde Yahoo Finance con reintentos."""
    for intento in range(1, reintentos + 1):
        try:
            raw = yf.download(ticker, start=inicio, end=fin, progress=False, auto_adjust=True)
            if raw is not None and not raw.empty:
                return raw
        except Exception as exc:
            print(f"[-] Intento {intento}/{reintentos} fallido para {ticker}: {exc}")
        time.sleep(2 * intento)
    return None


def preparar_activo(ticker, inicio=VENTANA_INICIO, fin=VENTANA_FIN):
    """
    Tubería estándar: descarga -> saneamiento -> retornos -> estados binarios.

    Devuelve un DataFrame con Date, Close, Return, Market_State, códigos de
    estado Code_N2/N3/N4 y Next_Return (retorno del día siguiente, que es el
    que captura la estrategia al operar sobre el estado observado hoy).
    Devuelve None si el activo no supera las validaciones de calidad.
    """
    raw = descargar_activo(ticker, inicio, fin)
    if raw is None:
        print(f"[-] ERROR: sin datos para {ticker}. Activo descartado.")
        return None

    df = raw.copy()
    # Yahoo entrega columnas multinivel al usar tickers con sufijos
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    df = df.reset_index()
    if "Date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "Date"})
    if "Close" not in df.columns and "Adj Close" in df.columns:
        df["Close"] = df["Adj Close"]

    # Saneamiento: nulos, precios no positivos, infinitos y fechas duplicadas
    df = df[["Date", "Close"]].dropna()
    df = df[np.isfinite(df["Close"]) & (df["Close"] > 0)]
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.drop_duplicates(subset="Date").sort_values("Date").reset_index(drop=True)

    df["Return"] = df["Close"].pct_change()
    df["Market_State"] = (df["Return"] > 0).astype(int)

    # Memoria de estados: t es el día actual, t1..t3 los anteriores
    df["State_t"] = df["Market_State"]
    df["State_t1"] = df["Market_State"].shift(1)
    df["State_t2"] = df["Market_State"].shift(2)
    df["State_t3"] = df["Market_State"].shift(3)
    df["Next_Return"] = df["Return"].shift(-1)
    df = df.dropna().copy()

    df["Code_N2"] = (df["State_t1"] * 2 + df["State_t"]).astype(int)
    df["Code_N3"] = (df["State_t2"] * 4 + df["State_t1"] * 2 + df["State_t"]).astype(int)
    df["Code_N4"] = (
        df["State_t3"] * 8 + df["State_t2"] * 4 + df["State_t1"] * 2 + df["State_t"]
    ).astype(int)

    if len(df) < MIN_VELAS:
        print(f"[-] ALERTA: {ticker} solo tiene {len(df)} velas saneadas (mínimo {MIN_VELAS}). Descartado.")
        return None

    return df.reset_index(drop=True)


def cargar_universo():
    """Prepara todos los activos del universo con la tubería estándar."""
    universo = {}
    for ticker, meta in ACTIVOS.items():
        print(f"[INGESTA] {meta['nombre']} ({ticker})...")
        df = preparar_activo(ticker)
        if df is not None:
            universo[ticker] = df
            print(f"[OK] {ticker}: {len(df)} velas saneadas "
                  f"({df['Date'].iloc[0].date()} -> {df['Date'].iloc[-1].date()})")
    return universo
