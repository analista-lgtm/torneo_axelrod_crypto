"""
Validación multi-horizonte de los pronósticos del tablero.

La Fase 2 validó el GJR-GARCH a 1 día en 18 mercados. El tablero ampliado
usa sus pronósticos multi-paso (5 y 21 días) en 36 mercados — tres
extrapolaciones sin sello propio. Este experimento las somete al protocolo
completo:

  - Objetivo a horizonte h: varianza realizada media de los próximos h
    días (proxy: promedio de retorno² sobre t+1..t+h). A h=21 el proxy es
    mucho menos ruidoso que a 1 día.
  - Contendientes: HIST-21 y EWMA (pronóstico plano, las varas) contra
    GJR-GARCH multi-paso (walk-forward con re-ajuste trimestral,
    recursión hacia la varianza incondicional — exactamente lo que
    alimenta el tablero).
  - Pérdida QLIKE; Diebold-Mariano del GJR contra cada vara con rezago
    Newey-West ampliado (h+2) por el solapamiento de las ventanas.
  - Período de selección (pre-2025-07) y sagrado por separado.

Salida: data/multi_activo/vol_multihorizonte.json (pestaña 🌡️).
"""
import json
import os
import warnings
from datetime import datetime, timezone
from math import erf, sqrt

import numpy as np
import pandas as pd

from src.data_pipeline import preparar_activo
from src.meta_portfolio_v2 import FIN, INICIO
from src.vol_monitor import UNIVERSO

warnings.filterwarnings("ignore")

DIR_SALIDA = "data/multi_activo"
SAGRADA = pd.Timestamp("2025-07-01")
HORIZONTES = [1, 5, 21]
WARMUP = 504
REFIT = 63
LAMBDA_EWMA = 0.94
PISO = 1e-12
MODELOS = ["HIST21", "EWMA", "GJR"]


def qlike(f, p):
    razon = np.maximum(p, PISO) / np.maximum(f, PISO)
    return razon - np.log(razon) - 1.0


def dm_test(perdida_modelo, perdida_ref, rezago):
    d = perdida_modelo - perdida_ref
    n = len(d)
    if n < 30:
        return None
    varianza = np.var(d, ddof=1)
    for k in range(1, rezago + 1):
        cov = np.cov(d[k:], d[:-k], ddof=1)[0, 1]
        varianza += 2 * (1 - k / (rezago + 1)) * cov
    se = np.sqrt(max(varianza, 1e-18) / n)
    stat = d.mean() / se
    return round(float(2 * (1 - 0.5 * (1 + erf(abs(stat) / sqrt(2))))), 4)


def pronosticos_gjr_multipaso(r):
    """Para cada t: varianza media prevista para los próximos h días (info <= t)."""
    from arch import arch_model
    n = len(r)
    prev = {h: np.full(n, np.nan) for h in HORIZONTES}
    params, sigma2 = None, None
    for t in range(WARMUP, n):
        if (t - WARMUP) % REFIT == 0:
            try:
                res = arch_model(pd.Series(r[:t + 1] * 100), mean="Zero", vol="GARCH",
                                 p=1, o=1, q=1, rescale=False).fit(disp="off", show_warning=False)
                p = res.params
                params = (float(p["omega"]), float(p["alpha[1]"]),
                          float(p["gamma[1]"]), float(p["beta[1]"]))
                sigma2 = float(res.conditional_volatility.iloc[-1] ** 2)
                persist = params[1] + params[2] / 2 + params[3]
                if not (0 < persist < 1):
                    params = None
            except Exception:
                params = None
        if params is None:
            continue
        w, a, g, b = params
        persist = a + g / 2 + b
        incond = w / (1 - persist)
        paso1 = w + a * (r[t] * 100) ** 2 + g * (r[t] * 100) ** 2 * (r[t] < 0) + b * sigma2
        sigma2 = max(paso1, 1e-8)
        esperadas = incond + persist ** np.arange(21) * (paso1 - incond)
        for h in HORIZONTES:
            prev[h][t] = float(np.mean(esperadas[:h])) / 1e4
    return prev


def main():
    print("=" * 70)
    print("   VALIDACION MULTI-HORIZONTE DE LOS PRONOSTICOS DEL TABLERO")
    print("=" * 70)

    universo = {}
    for tk in UNIVERSO:
        df = preparar_activo(tk, inicio=INICIO, fin=FIN)
        if df is not None:
            universo[tk] = df
    print(f"\n[*] {len(universo)} mercados | horizontes {HORIZONTES} dias")

    por_mercado = {}
    acumulado = {h: {m: {"sel": [], "sag": []} for m in MODELOS} for h in HORIZONTES}
    conteos = {h: {"gjr_gana_hist": 0, "gjr_gana_ewma": 0,
                   "dm_sig_hist": 0, "dm_sig_ewma": 0} for h in HORIZONTES}

    for tk, df in universo.items():
        nombre = UNIVERSO[tk][0]
        fechas = pd.DatetimeIndex(df["Date"])
        r = df["Return"].to_numpy(dtype=np.float64)
        n = len(r)
        r2 = r ** 2
        rv21 = pd.Series(r2).rolling(21).mean().to_numpy()
        ewma = pd.Series(r2).ewm(alpha=1 - LAMBDA_EWMA).mean().to_numpy()
        prev_gjr = pronosticos_gjr_multipaso(r)

        fila = {"nombre": nombre, "horizontes": {}}
        for h in HORIZONTES:
            # proxy: varianza media realizada en t+1..t+h
            proxy = pd.Series(r2).shift(-h).rolling(h).mean().shift(h - 1).to_numpy()
            # equivalente a mean(r2[t+1..t+h]); recomputo directo para claridad:
            proxy = np.array([r2[t + 1:t + 1 + h].mean() if t + h < n else np.nan
                              for t in range(n)])
            pron = {"HIST21": rv21, "EWMA": ewma, "GJR": prev_gjr[h]}
            valido = ~np.isnan(prev_gjr[h]) & ~np.isnan(proxy) & ~np.isnan(rv21)
            es_sag = np.asarray(fechas >= SAGRADA) & valido
            es_sel = valido & ~es_sag

            perdidas = {m: qlike(pron[m], proxy) for m in MODELOS}
            q = {}
            for m in MODELOS:
                q[m] = {
                    "sel": round(float(np.nanmean(perdidas[m][es_sel])), 4) if es_sel.sum() else None,
                    "sag": round(float(np.nanmean(perdidas[m][es_sag])), 4) if es_sag.sum() else None,
                }
                if q[m]["sel"] is not None:
                    acumulado[h][m]["sel"].append(q[m]["sel"])
                if q[m]["sag"] is not None:
                    acumulado[h][m]["sag"].append(q[m]["sag"])

            dm_hist = dm_test(perdidas["GJR"][es_sel], perdidas["HIST21"][es_sel], rezago=h + 2)
            dm_ewma = dm_test(perdidas["GJR"][es_sel], perdidas["EWMA"][es_sel], rezago=h + 2)
            gana_hist = q["GJR"]["sel"] is not None and q["GJR"]["sel"] < q["HIST21"]["sel"]
            gana_ewma = q["GJR"]["sel"] is not None and q["GJR"]["sel"] < q["EWMA"]["sel"]
            conteos[h]["gjr_gana_hist"] += gana_hist
            conteos[h]["gjr_gana_ewma"] += gana_ewma
            conteos[h]["dm_sig_hist"] += bool(gana_hist and dm_hist is not None and dm_hist < 0.05)
            conteos[h]["dm_sig_ewma"] += bool(gana_ewma and dm_ewma is not None and dm_ewma < 0.05)

            fila["horizontes"][str(h)] = {
                "qlike": {m: q[m]["sel"] for m in MODELOS},
                "qlike_sag": {m: q[m]["sag"] for m in MODELOS},
                "dm_gjr_vs_hist": dm_hist,
                "dm_gjr_vs_ewma": dm_ewma,
            }
        por_mercado[tk] = fila
        r21 = fila["horizontes"]["21"]["qlike"]
        print(f"  {nombre:<26}: h21 QLIKE GJR={r21['GJR']} HIST={r21['HIST21']} EWMA={r21['EWMA']}")

    n_m = len(por_mercado)
    global_json = {}
    for h in HORIZONTES:
        global_json[str(h)] = {
            "qlike_prom_sel": {m: round(float(np.mean(acumulado[h][m]["sel"])), 4) for m in MODELOS},
            "qlike_prom_sag": {m: round(float(np.mean(acumulado[h][m]["sag"])), 4) for m in MODELOS},
            **{k: int(v) for k, v in conteos[h].items()},
        }
        g = global_json[str(h)]
        print(f"\n[H={h}d] QLIKE sel: GJR {g['qlike_prom_sel']['GJR']} | HIST {g['qlike_prom_sel']['HIST21']} "
              f"| EWMA {g['qlike_prom_sel']['EWMA']}")
        print(f"        GJR gana a HIST en {g['gjr_gana_hist']}/{n_m} (DM sig. {g['dm_sig_hist']}) "
              f"| a EWMA en {g['gjr_gana_ewma']}/{n_m} (DM sig. {g['dm_sig_ewma']})")

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metodologia": "Proxy: varianza realizada media de los próximos h días. GJR multi-paso walk-forward (refit trimestral) vs varas planas HIST-21 y EWMA. QLIKE; DM con Newey-West de rezago h+2 (solapamiento); selección pre-2025-07 y sagrado aparte.",
        "horizontes": HORIZONTES,
        "num_mercados": n_m,
        "global": global_json,
        "por_mercado": por_mercado,
    }
    os.makedirs(DIR_SALIDA, exist_ok=True)
    with open(f"{DIR_SALIDA}/vol_multihorizonte.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    print(f"\n[+] Resultados exportados a {DIR_SALIDA}/vol_multihorizonte.json")


if __name__ == "__main__":
    main()
