"""
Tablero de Volatilidad — Fase 1 (monitoreo, sin modelos todavía).

La volatilidad es la única variable del laboratorio con predecibilidad
demostrada (se agrupa en regímenes). Este módulo calcula, para los 18
mercados del universo extendido, el panel completo de métricas:

  Por mercado:
    - Volatilidad realizada anualizada a 5/21/63/252 días.
    - Estimadores OHLC eficientes: Parkinson y Yang-Zhang (21d).
    - EWMA (RiskMetrics, lambda=0.94).
    - Vol-of-vol: variabilidad de la propia volatilidad (63d).
    - Percentil histórico de la vol actual (semáforo de régimen 0-100).
    - Estructura temporal (vol 5d / vol 63d): >1.3 = shock en curso.
    - Efecto apalancamiento: corr(retorno, cambio de vol) a 252d.
    - Serie mensual de vol 21d para el gráfico histórico.

  Del sistema:
    - Correlación media entre los 18 mercados (ventana 126d, mensual).
    - Absorption ratio: % de varianza explicada por el primer componente
      principal (acoplamiento sistémico; picos = fragilidad).
    - % de mercados en régimen de vol alta (percentil > 80).

  Implícitas públicas (Yahoo): VIX (S&P 500), OVX (petróleo), GVZ (oro),
  y la prima de riesgo de volatilidad del S&P (VIX - realizada 21d).

Salida: data/multi_activo/volatilidad.json (pestaña 🌡️ del dashboard).
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

from src.data_pipeline import preparar_activo
from src.meta_portfolio_v2 import FIN, INICIO, MERCADOS

DIR_SALIDA = "data/multi_activo"
VENTANAS = [5, 21, 63, 252]
LAMBDA_EWMA = 0.94
VENTANA_SISTEMA = 126
IMPLICITAS = {"^VIX": "VIX (S&P 500)", "^OVX": "OVX (Petróleo)", "^GVZ": "GVZ (Oro)"}
ANN = {"BTC-USD": 365, "ETH-USD": 365}   # el resto anualiza a 252


def ann_de(t):
    return ANN.get(t, 252)


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
    var_n = nocturno.rolling(n).var()
    var_ac = apertura_cierre.rolling(n).var()
    var_rs = rs.rolling(n).mean()
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    return np.sqrt((var_n + k * var_ac + (1 - k) * var_rs).clip(lower=0)) * np.sqrt(ann) * 100


def spark_mensual(serie, fechas):
    s = pd.Series(serie.to_numpy(), index=pd.DatetimeIndex(fechas)).dropna()
    m = s.resample("ME").last().dropna()
    return {"labels": [x.strftime("%Y-%m") for x in m.index],
            "valores": [round(float(v), 2) for v in m]}


def main():
    print("=" * 70)
    print("   TABLERO DE VOLATILIDAD - FASE 1 (18 MERCADOS + SISTEMA)")
    print("=" * 70)

    universo = {}
    for tk in MERCADOS:
        df = preparar_activo(tk, inicio=INICIO, fin=FIN)
        if df is not None:
            universo[tk] = df
    print(f"\n[*] {len(universo)} mercados aceptados")

    mercados_json = {}
    retornos = {}
    alertas = []
    for t, df in universo.items():
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
        apalancamiento = float(ret.rolling(252).corr(v21.diff()).iloc[-1])

        alertas_m = []
        if percentil >= 90:
            alertas_m.append("vol en percentil extremo")
            alertas.append({"nivel": "alto", "texto": f"{MERCADOS[t]}: volatilidad en percentil {percentil:.0f} de su historia"})
        if ratio_ts is not None and ratio_ts >= 1.3:
            alertas_m.append("estructura temporal invertida (shock)")
            alertas.append({"nivel": "medio", "texto": f"{MERCADOS[t]}: vol de 5d es {ratio_ts:.1f}x la de 63d — shock en curso"})

        mercados_json[t] = {
            "nombre": MERCADOS[t],
            "ann": ann,
            "vol": {k: round(float(v.iloc[-1]), 2) for k, v in vols.items()},
            "ewma": round(float(ewma.iloc[-1]), 2),
            "parkinson21": round(float(pk.iloc[-1]), 2) if pk is not None and np.isfinite(pk.iloc[-1]) else None,
            "yang_zhang21": round(float(yz.iloc[-1]), 2) if yz is not None and np.isfinite(yz.iloc[-1]) else None,
            "vol_of_vol": round(float(vol_of_vol.iloc[-1]), 1) if np.isfinite(vol_of_vol.iloc[-1]) else None,
            "percentil": round(percentil, 1),
            "ratio_ts": round(ratio_ts, 2) if ratio_ts is not None else None,
            "apalancamiento": round(apalancamiento, 2) if np.isfinite(apalancamiento) else None,
            "alertas": alertas_m,
            "spark": spark_mensual(v21, df["Date"]),
        }
        print(f"  {MERCADOS[t]:<26}: vol21 {mercados_json[t]['vol']['v21']:>6}% "
              f"| percentil {percentil:>5.1f} | TS {mercados_json[t]['ratio_ts']}")

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
            implicitas_json[tk] = {
                "nombre": nombre,
                "actual": round(float(s.iloc[-1]), 2),
                "percentil": round(float((s <= s.iloc[-1]).mean()) * 100, 1),
                "spark": {"labels": [x.strftime("%Y-%m") for x in s.resample("ME").last().dropna().index],
                          "valores": [round(float(v), 2) for v in s.resample("ME").last().dropna()]},
            }
        except Exception as exc:
            print(f"  [-] {tk} no disponible: {exc}")

    vrp = None
    if "^VIX" in implicitas_json and "SPY" in mercados_json:
        vrp = round(implicitas_json["^VIX"]["actual"] - mercados_json["SPY"]["vol"]["v21"], 2)

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ventana": {"inicio": INICIO, "fin": FIN},
        "mercados": mercados_json,
        "sistema": {
            "labels": labels_sis,
            "correlacion_media": corr_media,
            "absorption": absorption,
            "correlacion_actual": corr_media[-1] if corr_media else None,
            "absorption_actual": absorption[-1] if absorption else None,
            "pct_mercados_vol_alta": pct_alta,
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
          f"| mercados en vol alta: {pct_alta}%")
    if vrp is not None:
        print(f"[VRP] VIX {implicitas_json['^VIX']['actual']} vs realizada SPY "
              f"{mercados_json['SPY']['vol']['v21']}% -> prima: {vrp} puntos")
    print(f"[ALERTAS] {len(alertas)} activas")
    print(f"[+] Resultados exportados a {DIR_SALIDA}/volatilidad.json")


if __name__ == "__main__":
    main()
