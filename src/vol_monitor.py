"""
Tablero de Volatilidad — versión ampliada: termómetros y pronósticos.

Monitorea ~36 mercados globales organizados por categoría (índices, renta
fija/crédito, divisas, metales, energía, agrícolas, cripto, inmobiliario)
y añade PRONÓSTICOS de volatilidad con el modelo ganador de la Fase 2
(GJR-GARCH, con EWMA de respaldo si el ajuste falla):

  Por mercado:
    - Volatilidad realizada anualizada a 5/21/63/252 días.
    - Estimadores OHLC eficientes: Parkinson y Yang-Zhang (21d).
    - EWMA (RiskMetrics, lambda=0.94) y vol-of-vol (63d).
    - Percentil histórico (semáforo de régimen 0-100).
    - Estructura temporal (vol 5d / vol 63d): >1.3 = shock en curso.
    - PRONÓSTICO GJR-GARCH de la vol anualizada esperada para el próximo
      día, semana (5d) y mes (21d), vía recursión multi-paso hacia la
      varianza incondicional, y la tendencia esperada (¿sube o baja?).

  Del sistema: correlación media rodante (126d), absorption ratio (PCA),
  % de mercados en vol alta, con series mensuales.

  Implícitas públicas: VIX/OVX/GVZ y la prima de riesgo de vol del S&P.

Salida: data/multi_activo/volatilidad.json (pestaña 🌡️ del dashboard).
"""
import json
import os
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

from src.data_pipeline import preparar_activo
from src.meta_portfolio_v2 import FIN, INICIO

warnings.filterwarnings("ignore")

DIR_SALIDA = "data/multi_activo"
VENTANAS = [5, 21, 63, 252]
LAMBDA_EWMA = 0.94
VENTANA_SISTEMA = 126
IMPLICITAS = {"^VIX": "VIX (S&P 500)", "^OVX": "OVX (Petróleo)", "^GVZ": "GVZ (Oro)"}

# Universo ampliado de termómetros, por categoría
UNIVERSO = {
    # Índices bursátiles
    "SPY": ("S&P 500 (EE.UU.)", "Índices"),
    "QQQ": ("Nasdaq 100", "Índices"),
    "IWM": ("Russell 2000", "Índices"),
    "EFA": ("Desarrollados ex-US", "Índices"),
    "EEM": ("Mercados Emergentes", "Índices"),
    "^N225": ("Nikkei 225 (Japón)", "Índices"),
    "^GDAXI": ("DAX 40 (Alemania)", "Índices"),
    "^FTSE": ("FTSE 100 (R. Unido)", "Índices"),
    "^HSI": ("Hang Seng (Hong Kong)", "Índices"),
    "^BVSP": ("Bovespa (Brasil)", "Índices"),
    # Renta fija y crédito
    "TLT": ("Bonos Tesoro 20+ años", "Renta fija"),
    "IEF": ("Bonos Tesoro 7-10 años", "Renta fija"),
    "HYG": ("Crédito High Yield", "Renta fija"),
    # Divisas
    "DX-Y.NYB": ("Índice Dólar (DXY)", "Divisas"),
    "EURUSD=X": ("Euro/Dólar", "Divisas"),
    "USDJPY=X": ("Dólar/Yen", "Divisas"),
    "GBPUSD=X": ("Libra/Dólar", "Divisas"),
    "AUDUSD=X": ("Dólar australiano", "Divisas"),
    "USDMXN=X": ("Dólar/Peso mexicano", "Divisas"),
    # Metales
    "GC=F": ("Oro", "Metales"),
    "SI=F": ("Plata", "Metales"),
    "HG=F": ("Cobre", "Metales"),
    "PL=F": ("Platino", "Metales"),
    # Energía
    "CL=F": ("Petróleo WTI", "Energía"),
    "BZ=F": ("Petróleo Brent", "Energía"),
    "NG=F": ("Gas Natural", "Energía"),
    # Agrícolas
    "ZC=F": ("Maíz", "Agrícolas"),
    "ZW=F": ("Trigo", "Agrícolas"),
    "KC=F": ("Café", "Agrícolas"),
    "SB=F": ("Azúcar", "Agrícolas"),
    # Criptomonedas
    "BTC-USD": ("Bitcoin", "Cripto"),
    "ETH-USD": ("Ethereum", "Cripto"),
    "SOL-USD": ("Solana", "Cripto"),
    "BNB-USD": ("BNB", "Cripto"),
    "XRP-USD": ("XRP", "Cripto"),
    # Inmobiliario
    "VNQ": ("REITs EE.UU.", "Inmobiliario"),
}

CRIPTO = {"BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"}


def ann_de(t):
    return 365 if t in CRIPTO else 252


def vol_realizada(ret, n, ann):
    return ret.rolling(n).std() * np.sqrt(ann) * 100


def parkinson(df, n, ann):
    if "High" not in df.columns or "Low" not in df.columns:
        return None
    hl = np.log(df["High"] / df["Low"]) ** 2
    return np.sqrt(hl.rolling(n).mean() / (4 * np.log(2))) * np.sqrt(ann) * 100


def yang_zhang(df, n, ann):
    if not all(c in df.columns for c in ("Open", "High", "Low")):
        return None
    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    nocturno = np.log(o / c.shift(1))
    apertura_cierre = np.log(c / o)
    rs = np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o)
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    var = nocturno.rolling(n).var() + k * apertura_cierre.rolling(n).var() + (1 - k) * rs.rolling(n).mean()
    return np.sqrt(var.clip(lower=0)) * np.sqrt(ann) * 100


def pronostico_gjr(ret, ann):
    """
    Pronóstico GJR-GARCH (ganador de la Fase 2) de la vol anualizada esperada
    para 1 día, 5 días y 21 días, vía recursión multi-paso hacia la varianza
    incondicional. Respaldo EWMA (pronóstico plano) si el ajuste falla.
    """
    r = ret.dropna().to_numpy(dtype=np.float64)
    ewma_var = float(pd.Series(r ** 2).ewm(alpha=1 - LAMBDA_EWMA).mean().iloc[-1])
    try:
        from arch import arch_model
        res = arch_model(pd.Series(r * 100), mean="Zero", vol="GARCH",
                         p=1, o=1, q=1, rescale=False).fit(disp="off", show_warning=False)
        p = res.params
        w, a, g, b = (float(p["omega"]), float(p["alpha[1]"]),
                      float(p["gamma[1]"]), float(p["beta[1]"]))
        persistencia = a + g / 2 + b
        sigma2_hoy = float(res.conditional_volatility.iloc[-1] ** 2)
        paso1 = w + a * (r[-1] * 100) ** 2 + g * (r[-1] * 100) ** 2 * (r[-1] < 0) + b * sigma2_hoy
        if not (0 < persistencia < 1):
            raise ValueError("persistencia fuera de rango")
        incond = w / (1 - persistencia)
        esperadas = [incond + persistencia ** (h - 1) * (paso1 - incond) for h in range(1, 22)]
        var_media = lambda k: float(np.mean(esperadas[:k])) / 1e4
        modelo = "GJR-GARCH"
        v1, v5, v21 = var_media(1), var_media(5), var_media(21)
    except Exception:
        modelo, v1 = "EWMA", ewma_var
        v5 = v21 = ewma_var
        persistencia = None
    a_pct = lambda v: round(float(np.sqrt(v * ann) * 100), 2)
    return {
        "modelo": modelo,
        "d1": a_pct(v1), "d5": a_pct(v5), "d21": a_pct(v21),
        "persistencia": round(persistencia, 3) if persistencia is not None else None,
    }


def spark_mensual(serie, fechas):
    s = pd.Series(serie.to_numpy(), index=pd.DatetimeIndex(fechas)).dropna()
    m = s.resample("ME").last().dropna()
    return {"labels": [x.strftime("%Y-%m") for x in m.index],
            "valores": [round(float(v), 2) for v in m]}


def main():
    print("=" * 70)
    print("   TABLERO DE VOLATILIDAD AMPLIADO: TERMOMETROS + PRONOSTICOS")
    print("=" * 70)

    universo = {}
    for tk in UNIVERSO:
        df = preparar_activo(tk, inicio=INICIO, fin=FIN)
        if df is not None:
            universo[tk] = df
    print(f"\n[*] {len(universo)} de {len(UNIVERSO)} mercados aceptados")

    mercados_json = {}
    retornos = {}
    alertas = []
    for t, df in universo.items():
        nombre, categoria = UNIVERSO[t]
        ann = ann_de(t)
        ret = df["Return"]
        retornos[t] = pd.Series(ret.to_numpy(), index=pd.DatetimeIndex(df["Date"]))

        vols = {f"v{n}": vol_realizada(ret, n, ann) for n in VENTANAS}
        v21 = vols["v21"]
        ewma = np.sqrt((ret ** 2).ewm(alpha=1 - LAMBDA_EWMA).mean()) * np.sqrt(ann) * 100
        pk = parkinson(df, 21, ann)
        yz = yang_zhang(df, 21, ann)
        log_v21 = np.log(v21.replace(0, np.nan))
        vol_of_vol = log_v21.diff().rolling(63).std() * np.sqrt(ann) * 100
        percentil = float((v21.dropna() <= v21.iloc[-1]).mean()) * 100
        ratio_ts = float(vols["v5"].iloc[-1] / vols["v63"].iloc[-1]) if vols["v63"].iloc[-1] > 0 else None

        prevista = pronostico_gjr(ret, ann)
        actual_21 = float(v21.iloc[-1])
        tendencia = "sube" if prevista["d21"] > actual_21 * 1.05 else (
            "baja" if prevista["d21"] < actual_21 * 0.95 else "estable")

        alertas_m = []
        if percentil >= 90:
            alertas_m.append("percentil extremo")
            alertas.append({"nivel": "alto", "texto": f"{nombre}: volatilidad en percentil {percentil:.0f} de su historia"})
        if ratio_ts is not None and ratio_ts >= 1.3:
            alertas_m.append("shock en curso")
            alertas.append({"nivel": "medio", "texto": f"{nombre}: vol de 5d es {ratio_ts:.1f}x la de 63d — shock en curso"})
        if tendencia == "sube" and percentil >= 75:
            alertas.append({"nivel": "medio", "texto": f"{nombre}: el pronóstico GJR espera MÁS volatilidad desde un percentil ya alto ({percentil:.0f})"})

        mercados_json[t] = {
            "nombre": nombre,
            "categoria": categoria,
            "ann": ann,
            "vol": {k: round(float(v.iloc[-1]), 2) for k, v in vols.items()},
            "ewma": round(float(ewma.iloc[-1]), 2),
            "parkinson21": round(float(pk.iloc[-1]), 2) if pk is not None and np.isfinite(pk.iloc[-1]) else None,
            "yang_zhang21": round(float(yz.iloc[-1]), 2) if yz is not None and np.isfinite(yz.iloc[-1]) else None,
            "vol_of_vol": round(float(vol_of_vol.iloc[-1]), 1) if np.isfinite(vol_of_vol.iloc[-1]) else None,
            "percentil": round(percentil, 1),
            "ratio_ts": round(ratio_ts, 2) if ratio_ts is not None else None,
            "prevista": prevista,
            "tendencia": tendencia,
            "alertas": alertas_m,
            "spark": spark_mensual(v21, df["Date"]),
        }
        print(f"  {nombre:<26} [{categoria:<12}]: vol21 {actual_21:>6.1f}% | pct {percentil:>5.1f} "
              f"| prev21d {prevista['d21']:>6.1f}% ({tendencia}) [{prevista['modelo']}]")

    # ---------------- Métricas del sistema ----------------
    matriz = pd.DataFrame(retornos).dropna()
    labels_sis, corr_media, absorption = [], [], []
    posiciones = matriz.index.to_series().resample("ME").last().dropna()
    for fecha in posiciones:
        ventana = matriz.loc[:fecha].tail(VENTANA_SISTEMA)
        if len(ventana) < VENTANA_SISTEMA:
            continue
        c = ventana.corr().to_numpy()
        n = c.shape[0]
        corr_media.append(round(float((c.sum() - n) / (n * (n - 1))), 3))
        eig = np.linalg.eigvalsh(c)
        absorption.append(round(float(eig[-1] / eig.sum()), 3))
        labels_sis.append(fecha.strftime("%Y-%m"))

    pct_alta = round(float(np.mean([m["percentil"] > 80 for m in mercados_json.values()])) * 100, 1)
    subiendo = round(float(np.mean([m["tendencia"] == "sube" for m in mercados_json.values()])) * 100, 1)
    if corr_media and corr_media[-1] > 0.4:
        alertas.append({"nivel": "alto", "texto": f"Correlación media del sistema elevada ({corr_media[-1]}): la diversificación se está evaporando"})
    if pct_alta >= 40:
        alertas.append({"nivel": "alto", "texto": f"{pct_alta:.0f}% de los mercados en régimen de vol alta"})

    # ---------------- Volatilidades implícitas públicas ----------------
    implicitas_json = {}
    for tk, nombre in IMPLICITAS.items():
        try:
            raw = yf.download(tk, start=INICIO, end=FIN, progress=False, auto_adjust=False)
            if raw is None or raw.empty:
                continue
            s = raw["Close"]
            if isinstance(s, pd.DataFrame):
                s = s.iloc[:, 0]
            s = s.dropna()
            m = s.resample("ME").last().dropna()
            implicitas_json[tk] = {
                "nombre": nombre,
                "actual": round(float(s.iloc[-1]), 2),
                "percentil": round(float((s <= s.iloc[-1]).mean()) * 100, 1),
                "spark": {"labels": [x.strftime("%Y-%m") for x in m.index],
                          "valores": [round(float(v), 2) for v in m]},
            }
        except Exception as exc:
            print(f"  [-] {tk} no disponible: {exc}")

    vrp = None
    if "^VIX" in implicitas_json and "SPY" in mercados_json:
        vrp = round(implicitas_json["^VIX"]["actual"] - mercados_json["SPY"]["prevista"]["d21"], 2)

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ventana": {"inicio": INICIO, "fin": FIN},
        "modelo_pronostico": "GJR-GARCH (ganador Fase 2), recursión multi-paso; EWMA de respaldo",
        "mercados": mercados_json,
        "sistema": {
            "labels": labels_sis,
            "correlacion_media": corr_media,
            "absorption": absorption,
            "correlacion_actual": corr_media[-1] if corr_media else None,
            "absorption_actual": absorption[-1] if absorption else None,
            "pct_mercados_vol_alta": pct_alta,
            "pct_vol_subiendo": subiendo,
        },
        "implicitas": implicitas_json,
        "vrp_spy": vrp,
        "alertas": alertas,
    }
    os.makedirs(DIR_SALIDA, exist_ok=True)
    with open(f"{DIR_SALIDA}/volatilidad.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)

    print(f"\n[SISTEMA] corr media: {salida['sistema']['correlacion_actual']} "
          f"| absorption: {salida['sistema']['absorption_actual']} "
          f"| vol alta: {pct_alta}% | pronostico al alza: {subiendo}%")
    if vrp is not None:
        print(f"[VRP] VIX {implicitas_json['^VIX']['actual']} vs prevista SPY 21d "
              f"{mercados_json['SPY']['prevista']['d21']}% -> prima: {vrp} puntos")
    print(f"[ALERTAS] {len(alertas)} activas")
    print(f"[+] Resultados exportados a {DIR_SALIDA}/volatilidad.json")


if __name__ == "__main__":
    main()
