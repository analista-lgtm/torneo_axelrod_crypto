# -*- coding: utf-8 -*-
"""Búsqueda top-down para ampliar el universo aprobado de ForeBank.

1. Ranking de los 11 sectores GICS por momentum (ETF proxy, mezcla 6m/12m).
2. Cupos por sector proporcionales a la fuerza del sector (todos representados,
   para que el scoring pueda rotar cuando cambie el liderazgo).
3. Dentro de cada sector: jugadores sólidos (liquidez > $200M ADV, 12-1 positivo
   preferente, vol moderada), ranking por 12-1, y selección greedy con tope de
   correlación 0.85 contra TODO lo ya seleccionado (independencia).
Datos: yfinance (no toca los límites de Polygon).
"""
import json
import numpy as np
import pandas as pd
import yfinance as yf

SECTOR_ETF = {
    "Technology": "XLK", "Communication Services": "XLC", "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP", "Health Care": "XLV", "Financials": "XLF",
    "Industrials": "XLI", "Energy": "XLE", "Utilities": "XLU",
    "Real Estate": "XLRE", "Materials": "XLB",
}

# Longlist por sector: líderes líquidos y reconocidos (excluye el universo actual)
LONGLIST = {
    "Technology": ["ORCL", "AVGO", "CRM", "AMD", "ANET", "NOW", "ADBE", "QCOM", "TXN", "LRCX", "AMAT", "KLAC", "PLTR", "DELL", "IBM"],
    "Communication Services": ["META", "NFLX", "DIS", "TMUS", "SPOT", "T", "VZ"],
    "Consumer Discretionary": ["AMZN", "TSLA", "HD", "LOW", "BKNG", "TJX", "NKE", "SBUX", "RCL", "GM"],
    "Consumer Staples": ["COST", "PEP", "MDLZ", "CL", "MO", "PM", "KMB", "KR", "TGT"],
    "Health Care": ["LLY", "UNH", "ABBV", "MRK", "TMO", "ABT", "ISRG", "AMGN", "GILD", "VRTX", "BSX", "DHR"],
    "Financials": ["JPM", "V", "MA", "BAC", "GS", "MS", "WFC", "AXP", "BLK", "SCHW", "PGR", "BRK-B"],
    "Industrials": ["GE", "RTX", "HON", "UNP", "DE", "LMT", "ETN", "PH", "EMR", "TT", "UPS", "BA"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "PSX", "OXY", "KMI"],
    "Utilities": ["NEE", "CEG", "VST", "DUK", "AEP", "EXC"],
    "Real Estate": ["PLD", "AMT", "EQIX", "SPG", "O"],
    "Materials": ["LIN", "FCX", "NUE", "SHW", "APD", "NEM", "SCCO"],
}

# Cartera/universo actual: los nuevos deben descorrelacionar también contra estos
ACTUALES = ["AAPL", "GOOGL", "WDC", "MU", "HBM", "TSM", "NVDA", "GLW", "CIEN", "B",
            "EQNR", "BHP", "PWR", "MTRN", "CVE", "CAT",
            "JNJ", "KO", "WMT", "BN", "SO", "PG", "MCD", "MSFT"]

CUPOS_TOTALES = 21
CORR_MAX = 0.85
ADV_MINIMO = 200e6  # $200M diarios

todos = sorted(set(sum(LONGLIST.values(), []) + ACTUALES + list(SECTOR_ETF.values())))
print(f"[1/4] Descargando {len(todos)} series (18 meses)...")
raw = yf.download(todos, start="2025-01-01", end="2026-07-14", progress=False, auto_adjust=True)
cierres = raw["Close"]
volumen = raw["Volume"]

print("[2/4] Ranking de sectores por momentum (mezcla 6m/12m del ETF)...")
fuerza = {}
for sector, etf in SECTOR_ETF.items():
    s = cierres[etf].dropna()
    r6 = s.iloc[-1] / s.iloc[-126] - 1 if len(s) > 126 else np.nan
    r12 = s.iloc[-1] / s.iloc[-252] - 1 if len(s) > 252 else (s.iloc[-1] / s.iloc[0] - 1)
    fuerza[sector] = 0.5 * r6 + 0.5 * (r12 if np.isfinite(r12) else r6)
ranking = sorted(fuerza.items(), key=lambda kv: -kv[1])
for i, (sec, f) in enumerate(ranking, 1):
    print(f"   {i:2}. {sec:26} {f:+.1%}")

# Cupos: top-3 -> 3, siguientes 4 -> 2, últimos 4 -> 1  (= 21)
cupos = {}
for i, (sec, _) in enumerate(ranking):
    cupos[sec] = 3 if i < 3 else (2 if i < 7 else 1)

print("\n[3/4] Métricas de solidez por candidato...")
rets = cierres.pct_change()
metricas = {}
for t in set(sum(LONGLIST.values(), [])):
    s = cierres[t].dropna() if t in cierres.columns else pd.Series(dtype=float)
    if len(s) < 260:
        continue
    sma200 = s.rolling(200).mean().iloc[-1]
    vol = rets[t].dropna().iloc[-252:].std() * np.sqrt(252)
    adv = (cierres[t] * volumen[t]).dropna().iloc[-63:].mean()
    metricas[t] = {
        "ret_12_1": s.iloc[-21] / s.iloc[-252] - 1,
        "sobre_200": bool(s.iloc[-1] > sma200),
        "vol": float(vol),
        "adv": float(adv),
    }

print("[4/4] Selección greedy con tope de correlación...")
corr = rets.iloc[-252:].corr()
seleccion = []
detalle = []
for sector, _ in ranking:
    n = cupos[sector]
    candidatos = [t for t in LONGLIST[sector] if t in metricas and metricas[t]["adv"] >= ADV_MINIMO]
    # sólidos primero: sobre su 200d y 12-1 descendente; los que están bajo 200d van al final
    candidatos.sort(key=lambda t: (not metricas[t]["sobre_200"], -metricas[t]["ret_12_1"]))
    elegidos = []
    for t in candidatos:
        if len(elegidos) >= n:
            break
        base = seleccion + ACTUALES + elegidos
        pares = [corr.loc[t, o] for o in base if o in corr.columns and t in corr.columns and np.isfinite(corr.loc[t, o])]
        peor = max(pares) if pares else 0.0
        if peor > CORR_MAX:
            detalle.append(f"   [skip] {t} ({sector}): corr máx {peor:.2f} con el pool")
            continue
        elegidos.append(t)
        detalle.append(f"   [OK]   {t:6} {sector:26} 12-1 {metricas[t]['ret_12_1']:+.1%}  "
                       f"{'>' if metricas[t]['sobre_200'] else '<'}200d  vol {metricas[t]['vol']:.0%}  "
                       f"ADV ${metricas[t]['adv']/1e6:,.0f}M  corr máx {peor:.2f}")
    seleccion += elegidos

print("\n".join(detalle))
print(f"\nSeleccionados: {len(seleccion)}")
salida = [{"ticker": t, "sector": next(s for s, lst in LONGLIST.items() if t in lst)} for t in seleccion]
with open("data/universo_ampliado.json", "w", encoding="utf-8") as f:
    json.dump({"ranking_sectores": {s: round(v, 4) for s, v in ranking}, "cupos": cupos, "nuevos": salida}, f, indent=2, ensure_ascii=False)
print("Guardado en data/universo_ampliado.json")
