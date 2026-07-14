"""
Fase 3 del plan de alineación ForeBank CM: el pipeline EXACTO de scoring ante el tribunal.

Hipótesis y reglas congeladas ANTES de correr en PREREGISTRO_FOREBANK.md (leerlo primero).
Réplica fiel de netlify/functions/lib/scoring/ (commit ed6666c del repo forebank-cm):
math.js, category-scores.js, engine.js, market-data-sync.js — con fundamentales y manual
overlay en el neutral exacto que produce el motor ante datos faltantes.

Variantes:
  A) Score complejo: top-16 elegibles por display_score, salida en actionState 'exit'.
  B) Núcleo simple:  top-16 por retorno 12-1 (skip-month), gate precio>SMA200.
  Benchmark: SPY buy & hold.

Salida: data/multi_activo/forebank_backtest.json + reporte en consola.
Ejecutar desde la raíz: .venv\\Scripts\\python -m src.forebank_backtest
"""
import json
import time

import numpy as np
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------- configuración
DESCARGA_INICIO = "2013-07-01"
DESCARGA_FIN = "2026-07-02"
EVAL_INICIO = "2015-07-01"
EVAL_FIN = "2025-07-01"        # exclusivo: el sagrado empieza aquí
SAGRADO_FIN = "2026-07-01"

N_CARTERA = 16
COSTO_POR_LADO = 0.0010        # 10 pb, convención del laboratorio
MIN_SESIONES = 260             # un nombre entra al universo con >=260 sesiones

RUTA_SALIDA = "data/multi_activo/forebank_backtest.json"

# Universo congelado (S&P 100 actual; GOOGL como única clase de Alphabet).
# Sesgo de supervivencia reconocido en el pre-registro: el veredicto es H2 (relativo).
UNIVERSO = {
    # Tecnología
    "AAPL": "technology", "MSFT": "technology", "NVDA": "technology", "AVGO": "technology",
    "ORCL": "technology", "CRM": "technology", "ADBE": "technology", "AMD": "technology",
    "INTC": "technology", "IBM": "technology", "TXN": "technology", "QCOM": "technology",
    "CSCO": "technology", "ACN": "technology", "INTU": "technology", "PLTR": "technology",
    "NOW": "technology",
    # Comunicaciones
    "GOOGL": "communication services", "META": "communication services",
    "NFLX": "communication services", "DIS": "communication services",
    "CMCSA": "communication services", "T": "communication services",
    "VZ": "communication services", "TMUS": "communication services",
    "CHTR": "communication services",
    # Consumo discrecional
    "AMZN": "consumer discretionary", "TSLA": "consumer discretionary",
    "HD": "consumer discretionary", "MCD": "consumer discretionary",
    "NKE": "consumer discretionary", "SBUX": "consumer discretionary",
    "LOW": "consumer discretionary", "BKNG": "consumer discretionary",
    "TGT": "consumer discretionary", "F": "consumer discretionary",
    "GM": "consumer discretionary",
    # Consumo básico
    "PG": "consumer staples", "KO": "consumer staples", "PEP": "consumer staples",
    "COST": "consumer staples", "WMT": "consumer staples", "PM": "consumer staples",
    "MO": "consumer staples", "CL": "consumer staples", "MDLZ": "consumer staples",
    "KHC": "consumer staples",
    # Salud
    "LLY": "health care", "UNH": "health care", "JNJ": "health care", "ABBV": "health care",
    "MRK": "health care", "TMO": "health care", "ABT": "health care", "DHR": "health care",
    "PFE": "health care", "AMGN": "health care", "ISRG": "health care", "GILD": "health care",
    "MDT": "health care", "BMY": "health care", "CVS": "health care",
    # Financieras
    "BRK-B": "financials", "JPM": "financials", "V": "financials", "MA": "financials",
    "BAC": "financials", "WFC": "financials", "GS": "financials", "MS": "financials",
    "SCHW": "financials", "AXP": "financials", "BLK": "financials", "C": "financials",
    "COF": "financials", "MET": "financials", "AIG": "financials", "USB": "financials",
    "BK": "financials", "PYPL": "financials",
    # Industriales
    "GE": "industrials", "CAT": "industrials", "RTX": "industrials", "HON": "industrials",
    "UNP": "industrials", "BA": "industrials", "DE": "industrials", "LMT": "industrials",
    "UPS": "industrials", "FDX": "industrials", "MMM": "industrials", "EMR": "industrials",
    "GD": "industrials",
    # Energía
    "XOM": "energy", "CVX": "energy", "COP": "energy",
    # Materiales
    "LIN": "materials", "DOW": "materials",
    # Utilities
    "NEE": "utilities", "SO": "utilities", "DUK": "utilities", "EXC": "utilities",
    # Real Estate
    "AMT": "real estate", "SPG": "real estate",
}

SECTOR_PROXY = {
    "technology": "XLK", "communication services": "XLC", "consumer discretionary": "XLY",
    "consumer staples": "XLP", "health care": "XLV", "financials": "XLF",
    "industrials": "XLI", "energy": "XLE", "utilities": "XLU", "real estate": "XLRE",
    "materials": "XLB",
}
BENCHMARK = "SPY"

# ------------------------------------------------- réplica exacta de math.js
SCORE_BUCKETS = np.array([10, 21, 30, 45, 60, 65, 70, 73, 75, 77, 80, 83, 85, 90, 95, 99])

MODEL_WEIGHTS = {
    "assetMomentum": 0.35, "sectorMomentum": 0.20, "trendDurability": 0.10,
    "quality": 0.15, "risk": 0.10, "valuation": 0.05, "manualOverlay": 0.05,
}

# Neutrales exactos del motor ante datos faltantes (ver PREREGISTRO_FOREBANK.md):
# quality/valuation: cada componente scoreFromRange(null) = 60 -> promedio 60.
# manual overlay: tiers standard/standard/standard/neutral/none =
#   0.25*75 + 0.25*75 + 0.20*75 + 0.20*70 + 0.10*60 = 72.5
QUALITY_NEUTRAL = 60.0
VALUATION_NEUTRAL = 60.0
MANUAL_OVERLAY_NEUTRAL = 72.5


def score_desde_tabla(valores, tabla):
    """Réplica de scoreFromRange sobre arrays: interpolación lineal con extremos
    saturados; NaN -> 60 (comportamiento exacto del motor ante datos faltantes)."""
    xs = np.array([p[0] for p in tabla], dtype=float)
    ys = np.array([p[1] for p in tabla], dtype=float)
    valores = np.asarray(valores, dtype=float)
    resultado = np.interp(valores, xs, ys)
    return np.where(np.isfinite(valores), resultado, 60.0)


def bucket_down(scores):
    """Réplica de bucketDown: clamp 0-100 y bucket inferior; NaN -> 10."""
    scores = np.clip(np.asarray(scores, dtype=float), 0, 100)
    indices = np.searchsorted(SCORE_BUCKETS, np.nan_to_num(scores, nan=0.0), side="right") - 1
    indices = np.clip(indices, 0, len(SCORE_BUCKETS) - 1)
    buckets = SCORE_BUCKETS[indices]
    return np.where(np.isfinite(scores), buckets, 10)


def indice_bucket(buckets):
    return np.searchsorted(SCORE_BUCKETS, buckets)


# --------------------------------------------------------------- ingesta
def descargar_cierres(tickers):
    """Descarga Close y Volume ajustados de Yahoo en bloques, con reintentos."""
    cierres, volumenes = {}, {}
    bloque = 25
    for i in range(0, len(tickers), bloque):
        lote = tickers[i:i + bloque]
        for intento in range(1, 4):
            try:
                raw = yf.download(lote, start=DESCARGA_INICIO, end=DESCARGA_FIN,
                                  progress=False, auto_adjust=True, group_by="ticker")
                break
            except Exception as exc:
                print(f"[-] Lote {i//bloque + 1} intento {intento}: {exc}")
                time.sleep(3 * intento)
        else:
            raise RuntimeError("Descarga fallida tras reintentos")
        for t in lote:
            try:
                df = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
                serie = df["Close"].dropna()
                if len(serie):
                    cierres[t] = serie
                    volumenes[t] = df["Volume"].reindex(serie.index)
            except KeyError:
                print(f"[-] Sin datos para {t}")
        time.sleep(1)
    precios = pd.DataFrame(cierres).sort_index()
    volumen = pd.DataFrame(volumenes).reindex(precios.index)
    indice = pd.to_datetime(precios.index)
    if indice.tz is not None:
        indice = indice.tz_localize(None)
    precios.index = indice
    volumen.index = indice
    return precios, volumen


# ------------------------------------------- métricas (réplica market-data-sync)
def metricas_diarias(precios, volumen, spy):
    """Series diarias por ticker, con las definiciones exactas de metricSet."""
    m = {}
    m["ret_3m"] = precios / precios.shift(63) - 1
    m["ret_6m"] = precios / precios.shift(126) - 1
    m["ret_12_1"] = precios.shift(21) / precios.shift(252) - 1
    sma50 = precios.rolling(50, min_periods=1).mean()
    sma200 = precios.rolling(200, min_periods=1).mean()
    m["precio_vs_200"] = precios / sma200 - 1
    m["ma50_vs_200"] = sma50 / sma200 - 1
    high252 = precios.rolling(252, min_periods=1).max()
    m["dist_max_52s"] = precios / high252 - 1

    spy_6m = spy / spy.shift(126) - 1
    m["rs_6m"] = m["ret_6m"].sub(spy_6m, axis=0)

    logret = np.log(precios / precios.shift(1))
    spy_logret = np.log(spy / spy.shift(1))
    # standardDeviation del motor es poblacional (ddof=0) sobre los últimos 252 log-retornos
    m["vol_1y"] = logret.rolling(252).std(ddof=0) * np.sqrt(252) * 100
    var_spy = spy_logret.rolling(252).var(ddof=0)
    cov = logret.rolling(252).cov(spy_logret, ddof=0)
    m["beta"] = cov.div(var_spy, axis=0)

    # max drawdown 1y en % sobre los últimos 252 cierres (pico corriente de la ventana)
    def dd_ventana(ventana):
        pico = np.maximum.accumulate(ventana)
        return ((ventana / pico) - 1).min() * 100
    m["maxdd_1y"] = precios.rolling(252, min_periods=2).apply(dd_ventana, raw=True)

    m["adv_63"] = (precios * volumen).rolling(63, min_periods=1).mean()

    # Convertir a % donde el motor usa pctChange*100
    for clave in ("ret_3m", "ret_6m", "ret_12_1", "precio_vs_200", "ma50_vs_200",
                  "dist_max_52s", "rs_6m"):
        m[clave] = m[clave] * 100
    return m


def _metricas_de_serie(base, spy_6m):
    s = {}
    s["ret_3m"] = (base / base.shift(63) - 1) * 100
    s["ret_6m"] = (base / base.shift(126) - 1) * 100
    s["ret_12m"] = (base / base.shift(252) - 1) * 100
    s["rs_6m"] = s["ret_6m"] - spy_6m
    sma200 = base.rolling(200, min_periods=1).mean()
    s["sobre_200"] = pd.Series(np.where(base.notna() & sma200.notna(),
                                        np.where(base >= sma200, 80.0, 40.0), np.nan),
                               index=base.index)
    return s


def metricas_sector(proxies, spy):
    """Métricas del ETF proxy por sector. Fallback a NIVEL DE MÉTRICA hacia SPY
    cuando el ETF aún no tiene historia suficiente (pre-registrado): empalmar
    precios crearía retornos artificiales en la costura."""
    spy_6m = (spy / spy.shift(126) - 1) * 100
    met_spy = _metricas_de_serie(spy, spy_6m)
    sector = {}
    for nombre, serie in proxies.items():
        propio = _metricas_de_serie(serie.reindex(spy.index), spy_6m)
        sector[nombre] = {campo: propio[campo].combine_first(met_spy[campo]) for campo in propio}
    return sector


# ------------------------------------------- score semanal (réplica engine.js)
TABLAS = {
    "am_12_1": [[-35, 10], [-15, 30], [0, 60], [10, 73], [20, 83], [35, 90], [60, 99]],
    "am_6m": [[-25, 10], [-10, 35], [0, 60], [8, 73], [16, 83], [28, 90], [45, 99]],
    "am_3m": [[-18, 10], [-8, 35], [0, 60], [5, 70], [10, 80], [18, 90], [30, 99]],
    "am_p200": [[-25, 10], [-10, 35], [0, 65], [8, 77], [18, 90], [30, 99]],
    "am_ma": [[-15, 10], [-5, 40], [0, 65], [5, 77], [12, 90], [22, 99]],
    "am_dist": [[-45, 10], [-25, 45], [-12, 70], [-5, 83], [0, 95]],
    "am_rs": [[-20, 10], [-8, 40], [0, 65], [8, 80], [18, 90], [30, 99]],
    "sm_12": [[-30, 10], [-12, 35], [0, 60], [10, 73], [20, 83], [35, 95]],
    "sm_6": [[-20, 10], [-8, 35], [0, 60], [8, 75], [16, 85], [28, 95]],
    "sm_3": [[-15, 10], [-6, 40], [0, 60], [5, 73], [10, 83], [20, 95]],
    "sm_rs": [[-15, 10], [-6, 40], [0, 65], [6, 78], [14, 90], [24, 99]],
    "sm_200": [[20, 10], [35, 40], [50, 60], [65, 75], [80, 90], [92, 99]],
    "td_slope": [[-10, 20], [0, 65], [8, 85], [18, 99]],
    "td_dd": [[-55, 10], [-35, 45], [-22, 65], [-12, 80], [-5, 95]],
    "td_voladj": [[-30, 10], [-10, 40], [0, 60], [10, 75], [22, 90], [38, 99]],
    "rk_beta": [[0.4, 95], [0.8, 85], [1.0, 75], [1.3, 60], [1.8, 35], [2.4, 10]],
    "rk_vol": [[8, 95], [15, 85], [22, 70], [32, 50], [50, 20], [70, 10]],
    "rk_dd": [[-60, 10], [-40, 35], [-25, 60], [-15, 75], [-8, 90], [-3, 99]],
    "rk_adv": [[1e6, 25], [5e6, 55], [25e6, 75], [1e8, 90], [5e8, 99]],
}


def score_semanal(sem, sec_sem, sectores_por_ticker):
    """Calcula raw/display/eligible/exit por (semana, ticker) con las fórmulas exactas."""
    t = lambda clave, matriz: score_desde_tabla(matriz.values, TABLAS[clave])

    asset_mom = (t("am_12_1", sem["ret_12_1"]) * 0.30 + t("am_6m", sem["ret_6m"]) * 0.20 +
                 t("am_3m", sem["ret_3m"]) * 0.10 + t("am_p200", sem["precio_vs_200"]) * 0.15 +
                 t("am_ma", sem["ma50_vs_200"]) * 0.10 + t("am_dist", sem["dist_max_52s"]) * 0.10 +
                 t("am_rs", sem["rs_6m"]) * 0.05)

    sector_mom = (score_desde_tabla(sec_sem["ret_12m"].values, TABLAS["sm_12"]) * 0.30 +
                  score_desde_tabla(sec_sem["ret_6m"].values, TABLAS["sm_6"]) * 0.25 +
                  score_desde_tabla(sec_sem["ret_3m"].values, TABLAS["sm_3"]) * 0.15 +
                  score_desde_tabla(sec_sem["rs_6m"].values, TABLAS["sm_rs"]) * 0.20 +
                  score_desde_tabla(sec_sem["sobre_200"].values, TABLAS["sm_200"]) * 0.10)

    vol_adj = sem["ret_12_1"].values - np.nan_to_num(sem["vol_1y"].values, nan=0.0) * 0.35
    trend_dur = (t("td_slope", sem["ma50_vs_200"]) * 0.35 + t("td_dd", sem["maxdd_1y"]) * 0.30 +
                 score_desde_tabla(vol_adj, TABLAS["td_voladj"]) * 0.35)

    # risk: market_cap sin dato -> 60 con peso 0.10 (idéntico al motor)
    riesgo = (t("rk_beta", sem["beta"]) * 0.25 + t("rk_vol", sem["vol_1y"]) * 0.25 +
              t("rk_dd", sem["maxdd_1y"]) * 0.25 + t("rk_adv", sem["adv_63"]) * 0.15 +
              60.0 * 0.10)

    raw = (asset_mom * MODEL_WEIGHTS["assetMomentum"] + sector_mom * MODEL_WEIGHTS["sectorMomentum"] +
           trend_dur * MODEL_WEIGHTS["trendDurability"] + QUALITY_NEUTRAL * MODEL_WEIGHTS["quality"] +
           riesgo * MODEL_WEIGHTS["risk"] + VALUATION_NEUTRAL * MODEL_WEIGHTS["valuation"] +
           MANUAL_OVERLAY_NEUTRAL * MODEL_WEIGHTS["manualOverlay"])

    # Caps y gates exactos de applyScoreCaps
    precio_bajo_200 = sem["precio_vs_200"].values < 0
    ma_bajo = sem["ma50_vs_200"].values < 0
    dd_severo = sem["maxdd_1y"].values <= -35
    mom_roto = asset_mom < 60
    sector_debil = sector_mom < 60

    capped = raw.copy()
    capped = np.where(precio_bajo_200, np.minimum(capped, 65), capped)
    capped = np.where(ma_bajo, np.minimum(capped, 70), capped)
    capped = np.where(dd_severo, np.minimum(capped, 75), capped)
    capped = np.where(mom_roto, np.minimum(capped, 65), capped)
    capped = np.where(sector_debil, np.minimum(capped, 70), capped)  # sleeve momentum

    display = bucket_down(capped)

    elegible = ((display >= 75) & (asset_mom >= 70) & (sector_mom >= 65) & ~precio_bajo_200 &
                np.isfinite(sem["ret_12_1"].values))
    # actionState 'exit': display<60 o momentum roto (manual_block no aplica)
    salida = (display < 60) | mom_roto
    return {"display": display, "elegible": elegible, "salida": salida,
            "asset_mom": asset_mom, "sector_mom": sector_mom, "raw": capped}


# --------------------------------------------------------------- simulación
def simular(decisiones, fechas, retornos, vol_1y, nombre):
    """Simulación diaria con rebalanceo mensual, 1/vol sobre lo invertido, Long/Cash.

    decisiones: dict fecha_decision -> lista de tickers objetivo (ya filtrada/rankeada).
    """
    valor = 1.0
    posiciones = {}   # ticker -> valor
    cash = 1.0
    curva = pd.Series(index=fechas, dtype=float)
    costos_totales = 0.0
    decision_dias = set(decisiones)

    for fecha in fechas:
        # 1) acumular retornos del día sobre las posiciones existentes
        if posiciones:
            r = retornos.loc[fecha]
            for tk in list(posiciones):
                ret = r.get(tk)
                if pd.notna(ret):
                    posiciones[tk] *= (1 + ret)
        valor = cash + sum(posiciones.values())

        # 2) rebalancear al cierre del día de decisión
        if fecha in decision_dias:
            objetivo = decisiones[fecha]
            vols = vol_1y.loc[:fecha].iloc[-1]
            inversos = {}
            for tk in objetivo:
                v = vols.get(tk)
                inversos[tk] = 1.0 / v if pd.notna(v) and v > 0 else np.nan
            mediana = np.nanmedian(list(inversos.values())) if inversos else np.nan
            pesos = {}
            total_inv = 0.0
            for tk, inv in inversos.items():
                inv = inv if np.isfinite(inv) else mediana
                if np.isfinite(inv):
                    pesos[tk] = inv
                    total_inv += inv
            fraccion_invertida = len(pesos) / N_CARTERA
            nuevos = {}
            if total_inv > 0:
                for tk, inv in pesos.items():
                    nuevos[tk] = valor * fraccion_invertida * (inv / total_inv)
            turnover = sum(abs(nuevos.get(tk, 0.0) - posiciones.get(tk, 0.0))
                           for tk in set(nuevos) | set(posiciones))
            costo = turnover * COSTO_POR_LADO
            costos_totales += costo
            valor -= costo
            escala = (valor * fraccion_invertida) / sum(nuevos.values()) if nuevos else 0.0
            posiciones = {tk: v * escala for tk, v in nuevos.items()}
            cash = valor - sum(posiciones.values())

        curva[fecha] = valor

    print(f"    [{nombre}] costos acumulados: {costos_totales:.4f} sobre capital 1.0")
    return curva


def metricas_curva(curva):
    r = curva.pct_change().dropna()
    if not len(r):
        return {}
    total = curva.iloc[-1] / curva.iloc[0] - 1
    anios = len(r) / 252
    cagr = (1 + total) ** (1 / anios) - 1 if anios > 0 else np.nan
    vol = r.std(ddof=1) * np.sqrt(252)
    sharpe = r.mean() / r.std(ddof=1) * np.sqrt(252) if r.std(ddof=1) > 0 else np.nan
    pico = curva.cummax()
    maxdd = ((curva / pico) - 1).min()
    return {"retorno_total": round(float(total), 4), "cagr": round(float(cagr), 4),
            "vol_anual": round(float(vol), 4), "sharpe": round(float(sharpe), 3),
            "max_drawdown": round(float(maxdd), 4)}


def t_stat_exceso_mensual(curva_a, curva_b):
    """t-stat del exceso de retorno mensual A-B."""
    ma = curva_a.resample("ME").last().pct_change().dropna()
    mb = curva_b.resample("ME").last().pct_change().dropna()
    comun = ma.index.intersection(mb.index)
    exceso = (ma[comun] - mb[comun]).values
    if len(exceso) < 12:
        return np.nan, len(exceso)
    t = exceso.mean() / (exceso.std(ddof=1) / np.sqrt(len(exceso)))
    return round(float(t), 3), len(exceso)


def main():
    inicio = time.time()
    print("=" * 74)
    print("FASE 3 FOREBANK: pipeline exacto de scoring ante el tribunal")
    print("Pre-registro: PREREGISTRO_FOREBANK.md (congelado antes de esta corrida)")
    print("=" * 74)

    tickers = list(UNIVERSO)
    proxies_necesarios = sorted(set(SECTOR_PROXY.values()))
    print(f"[1/5] Descargando {len(tickers)} nombres + {len(proxies_necesarios)} proxies + SPY...")
    precios, volumen = descargar_cierres(tickers + proxies_necesarios + [BENCHMARK])

    spy = precios[BENCHMARK].dropna()
    universo_ok = [t for t in tickers if t in precios.columns and precios[t].notna().sum() >= MIN_SESIONES]
    print(f"      {len(universo_ok)} nombres con >= {MIN_SESIONES} sesiones")

    px = precios[universo_ok].reindex(spy.index)
    vol_shares = volumen[universo_ok].reindex(spy.index)

    print("[2/5] Calculando métricas diarias (réplica de metricSet)...")
    met = metricas_diarias(px, vol_shares, spy)
    proxies = {s: precios[e].reindex(spy.index) for s, e in SECTOR_PROXY.items() if e in precios.columns}
    met_sector = metricas_sector(proxies, spy)

    # Cada nombre exige >=MIN_SESIONES de historia antes de puntuar (pre-registrado)
    obs_acum = px.notna().cumsum()
    px_valido = obs_acum >= MIN_SESIONES

    # Semanas: último día hábil de cada semana calendario
    semanas = pd.Series(spy.index, index=spy.index).groupby(spy.index.to_period("W")).last()
    semanas = pd.DatetimeIndex(semanas.values)

    print(f"[3/5] Scoring semanal exacto en {len(semanas)} semanas...")
    sem = {k: v.reindex(semanas) for k, v in met.items()}
    # matriz sectorial alineada (semanas x tickers) según el sector de cada nombre
    sec_sem = {}
    for campo in ("ret_3m", "ret_6m", "ret_12m", "rs_6m", "sobre_200"):
        columnas = {}
        for tk in universo_ok:
            columnas[tk] = met_sector[UNIVERSO[tk]][campo].reindex(semanas)
        sec_sem[campo] = pd.DataFrame(columnas)

    s = score_semanal(sem, sec_sem, UNIVERSO)
    valido = px_valido.reindex(semanas).values & np.isfinite(sem["ret_12_1"].values)
    display = pd.DataFrame(np.where(valido, s["display"], np.nan), index=semanas, columns=universo_ok)
    elegible = pd.DataFrame(s["elegible"] & valido, index=semanas, columns=universo_ok)
    salida_score = pd.DataFrame(np.where(valido, s["salida"], True), index=semanas, columns=universo_ok).astype(bool)
    raw = pd.DataFrame(np.where(valido, s["raw"], np.nan), index=semanas, columns=universo_ok)

    # Núcleo simple: 12-1 y gate 200d en las mismas semanas
    sig_12_1 = pd.DataFrame(np.where(valido, sem["ret_12_1"].values, np.nan), index=semanas, columns=universo_ok)
    gate_200 = pd.DataFrame((sem["precio_vs_200"].values > 0) & valido, index=semanas, columns=universo_ok)

    print("[4/5] Simulación mensual 2015-07 -> 2026-07 (una sola corrida por variante)...")
    fechas = spy.index[(spy.index >= EVAL_INICIO) & (spy.index < SAGRADO_FIN)]
    retornos = px.pct_change().reindex(fechas)
    meses = pd.Series(fechas, index=fechas).groupby(fechas.to_period("M")).first()
    dias_decision = pd.DatetimeIndex(meses.values)

    def ultima_semana_antes(fecha):
        previas = semanas[semanas < fecha]
        return previas[-1] if len(previas) else None

    decisiones_a, decisiones_b = {}, {}
    cartera_a, cartera_b = [], []
    for dia in dias_decision:
        w = ultima_semana_antes(dia)
        if w is None:
            continue
        # Variante A: score complejo
        fila_salida = salida_score.loc[w]
        cartera_a = [tk for tk in cartera_a if not fila_salida[tk]]
        if len(cartera_a) < N_CARTERA:
            fila_e = elegible.loc[w]
            candidatos = [tk for tk in universo_ok if fila_e[tk] and tk not in cartera_a]
            candidatos.sort(key=lambda tk: (-display.loc[w, tk], -raw.loc[w, tk], tk))
            cartera_a += candidatos[:N_CARTERA - len(cartera_a)]
        decisiones_a[dia] = list(cartera_a)
        # Variante B: núcleo simple
        fila_gate = gate_200.loc[w]
        cartera_b = [tk for tk in cartera_b if fila_gate[tk]]
        if len(cartera_b) < N_CARTERA:
            fila_s = sig_12_1.loc[w]
            candidatos = [tk for tk in universo_ok
                          if fila_gate[tk] and pd.notna(fila_s[tk]) and fila_s[tk] > 0 and tk not in cartera_b]
            candidatos.sort(key=lambda tk: (-fila_s[tk], tk))
            cartera_b += candidatos[:N_CARTERA - len(cartera_b)]
        decisiones_b[dia] = list(cartera_b)

    vol_diaria = met["vol_1y"]
    curva_a = simular(decisiones_a, fechas, retornos, vol_diaria, "A score complejo")
    curva_b = simular(decisiones_b, fechas, retornos, vol_diaria, "B nucleo simple")
    curva_spy = (1 + spy.pct_change().reindex(fechas).fillna(0)).cumprod()

    print("[5/5] Métricas, multi-corte y sagrado...")
    resultados = {}
    for nombre, curva in (("score_complejo", curva_a), ("nucleo_simple", curva_b), ("spy", curva_spy)):
        ev = curva[(curva.index >= EVAL_INICIO) & (curva.index < EVAL_FIN)]
        sg = curva[(curva.index >= EVAL_FIN) & (curva.index < SAGRADO_FIN)]
        resultados[nombre] = {"evaluacion": metricas_curva(ev), "sagrado": metricas_curva(sg)}

    # multi-corte anual (evaluación)
    cortes = {}
    for anio in range(2016, 2025):
        ini, fin = f"{anio}-01-01", f"{anio + 1}-01-01"
        fila = {}
        for nombre, curva in (("A", curva_a), ("B", curva_b), ("SPY", curva_spy)):
            tramo = curva[(curva.index >= ini) & (curva.index < fin)]
            fila[nombre] = metricas_curva(tramo).get("sharpe")
        cortes[str(anio)] = fila

    ev_a = curva_a[(curva_a.index >= EVAL_INICIO) & (curva_a.index < EVAL_FIN)]
    ev_b = curva_b[(curva_b.index >= EVAL_INICIO) & (curva_b.index < EVAL_FIN)]
    ev_spy = curva_spy[(curva_spy.index >= EVAL_INICIO) & (curva_spy.index < EVAL_FIN)]
    t_h1, n_h1 = t_stat_exceso_mensual(ev_a, ev_spy)
    t_h2, n_h2 = t_stat_exceso_mensual(ev_a, ev_b)

    sharpe_a = resultados["score_complejo"]["evaluacion"].get("sharpe")
    sharpe_b = resultados["nucleo_simple"]["evaluacion"].get("sharpe")
    sharpe_spy = resultados["spy"]["evaluacion"].get("sharpe")
    veredicto = {
        "H1_score_supera_spy": bool(sharpe_a > sharpe_spy),
        "H2_score_supera_nucleo": bool(sharpe_a > sharpe_b),
        "t_stat_exceso_vs_spy": t_h1, "meses_h1": n_h1,
        "t_stat_exceso_vs_nucleo": t_h2, "meses_h2": n_h2,
        "anios_A_gana_B": sum(1 for f in cortes.values()
                              if f["A"] is not None and f["B"] is not None and f["A"] > f["B"]),
        "anios_totales": len(cortes),
    }

    salida = {
        "preregistro": "PREREGISTRO_FOREBANK.md",
        "universo": len(universo_ok),
        "ventanas": {"evaluacion": [EVAL_INICIO, EVAL_FIN], "sagrado": [EVAL_FIN, SAGRADO_FIN]},
        "parametros": {"n_cartera": N_CARTERA, "costo_por_lado": COSTO_POR_LADO},
        "resultados": resultados,
        "multi_corte_sharpe_anual": cortes,
        "veredicto": veredicto,
    }
    with open(RUTA_SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    print()
    print(f"{'':22} {'Sharpe':>7} {'CAGR':>8} {'MaxDD':>8}   (evaluación 2015-07 -> 2025-07)")
    for nombre in ("score_complejo", "nucleo_simple", "spy"):
        r = resultados[nombre]["evaluacion"]
        print(f"  {nombre:20} {r.get('sharpe', float('nan')):>7} {r.get('cagr', float('nan')):>8.2%} {r.get('max_drawdown', float('nan')):>8.2%}")
    print()
    print(f"  H1 (score > SPY):    {veredicto['H1_score_supera_spy']}  (t exceso mensual {t_h1}, n={n_h1})")
    print(f"  H2 (score > núcleo): {veredicto['H2_score_supera_nucleo']}  (t exceso mensual {t_h2}, n={n_h2})")
    print(f"  Multi-corte: A gana a B en {veredicto['anios_A_gana_B']}/{veredicto['anios_totales']} años")
    print()
    print("  SAGRADO (2025-07 -> 2026-07, una sola pasada):")
    for nombre in ("score_complejo", "nucleo_simple", "spy"):
        r = resultados[nombre]["sagrado"]
        print(f"  {nombre:20} Sharpe {r.get('sharpe')}  ret {r.get('retorno_total', float('nan')):.2%}  DD {r.get('max_drawdown', float('nan')):.2%}")
    print(f"\n  Resultado guardado en {RUTA_SALIDA} ({time.time() - inicio:.0f}s)")


if __name__ == "__main__":
    main()
