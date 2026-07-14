"""
Tablero de Volatilidad — Fase 2: el Torneo de Modelos de Pronóstico.

Cinco modelos compiten para predecir la varianza del día siguiente en cada
uno de los 18 mercados, bajo el protocolo pre-registrado del ROADMAP:

  Varas (baselines):
    - HIST-21: varianza histórica de 21 días (la persistencia sensata).
    - EWMA: RiskMetrics (lambda = 0.94).
  Hipótesis primaria:
    - HAR-RV (Corsi 2009): regresión de la varianza de mañana sobre la de
      ayer, la semana y el mes. Re-estimada trimestralmente, expansiva.
  Retadores:
    - GJR-GARCH(1,1): captura el efecto apalancamiento (las caídas suben
      la vol más que las subidas). Ajustado con `arch`, recursión manual
      entre re-ajustes trimestrales.
    - LightGBM: gradient boosting con features multi-horizonte y el factor
      de volatilidad GLOBAL (spillovers entre mercados — nuestra ventaja
      de tener 18 mercados en una tubería estándar).

Protocolo de evaluación (todo causal, walk-forward expansivo):
  - Objetivo: varianza realizada de t+1 (proxy: retorno² de t+1).
  - Pérdida: QLIKE (Patton 2011) — robusta al ruido del proxy y la
    estándar de la literatura de pronóstico de volatilidad.
  - Test de Diebold-Mariano (errores Newey-West) de cada modelo contra
    HAR, en el período de selección (pre-2025-07).
  - Período sagrado (2025-07 →) reportado por separado.
  - Regla pre-registrada: un modelo "predice" solo si vence a HIST-21 Y
    a HAR con DM p<0.05 en la mayoría de los mercados.

Salida: data/multi_activo/vol_modelos.json (pestaña 🌡️ del dashboard).
"""
import json
import os
import warnings
from datetime import datetime, timezone
from math import erf, sqrt

import numpy as np
import pandas as pd

from src.data_pipeline import preparar_activo
from src.meta_portfolio_v2 import FIN, INICIO, MERCADOS

warnings.filterwarnings("ignore")

DIR_SALIDA = "data/multi_activo"
SAGRADA = pd.Timestamp("2025-07-01")
WARMUP = 504          # dos años antes del primer pronóstico
REFIT = 63            # re-estimación trimestral
LAMBDA_EWMA = 0.94
PISO = 1e-12
MODELOS = ["HIST21", "EWMA", "HAR", "GJR-GARCH", "LightGBM"]


def qlike(pronostico, proxy):
    f = np.maximum(pronostico, PISO)
    p = np.maximum(proxy, PISO)
    razon = p / f
    return razon - np.log(razon) - 1.0


def dm_test(perdida_modelo, perdida_ref, rezago=5):
    """Diebold-Mariano con errores Newey-West. Negativo = el modelo es mejor."""
    d = perdida_modelo - perdida_ref
    n = len(d)
    if n < 30:
        return None, None
    media = d.mean()
    gamma0 = np.var(d, ddof=1)
    varianza = gamma0
    for k in range(1, rezago + 1):
        cov = np.cov(d[k:], d[:-k], ddof=1)[0, 1]
        varianza += 2 * (1 - k / (rezago + 1)) * cov
    se = np.sqrt(varianza / n)
    if se == 0:
        return None, None
    stat = media / se
    p = 2 * (1 - 0.5 * (1 + erf(abs(stat) / sqrt(2))))
    return round(float(stat), 2), round(float(p), 4)


def ajustar_gjr(retornos_pct):
    from arch import arch_model
    am = arch_model(retornos_pct, mean="Zero", vol="GARCH", p=1, o=1, q=1, rescale=False)
    res = am.fit(disp="off", show_warning=False)
    p = res.params
    return (float(p.get("omega", 0)), float(p.get("alpha[1]", 0)),
            float(p.get("gamma[1]", 0)), float(p.get("beta[1]", 0)),
            float(res.conditional_volatility.iloc[-1] ** 2))


def pronosticos_mercado(r, factor_global):
    """Matriz de pronósticos de varianza (n, modelos) con información <= t para t+1."""
    n = len(r)
    r2 = r ** 2
    rv5 = pd.Series(r2).rolling(5).mean().to_numpy()
    rv21 = pd.Series(r2).rolling(21).mean().to_numpy()
    rv22 = pd.Series(r2).rolling(22).mean().to_numpy()
    rv63 = pd.Series(r2).rolling(63).mean().to_numpy()
    ewma = pd.Series(r2).ewm(alpha=1 - LAMBDA_EWMA).mean().to_numpy()

    pron = {m: np.full(n, np.nan) for m in MODELOS}
    import lightgbm as lgb

    log = lambda x: np.log(np.maximum(x, PISO))
    features = np.column_stack([
        log(r2), log(rv5), log(rv22), log(rv63),
        r, np.abs(r), log(factor_global),
        np.divide(rv5, np.maximum(rv63, PISO)),
    ])

    params_gjr, sigma2 = None, None
    betas_har, modelo_lgb = None, None
    f_min, f_max = PISO, np.inf

    for t in range(WARMUP, n - 1):
        if (t - WARMUP) % REFIT == 0:
            # ---- Re-estimación trimestral con datos hasta t (inclusive) ----
            # Winsorización estándar: los outliers extremos de varianza (tipo
            # abril-2020 en petróleo) desestabilizan la OLS en niveles y el
            # target logarítmico del ML. Se recortan al rango [0.5%, 99.5%]
            # del entrenamiento, y los pronósticos se acotan a un rango de
            # cordura derivado también solo del pasado (sin mirar el futuro).
            lo, hi = np.quantile(r2[21:t], 0.005), np.quantile(r2[21:t], 0.995)
            f_min = max(np.quantile(r2[21:t], 0.01), PISO)
            f_max = np.quantile(r2[21:t], 0.999) * 3
            w = lambda x: np.clip(x, lo, hi)
            X = np.column_stack([np.ones(t - 22), w(r2[21:t - 1]), w(rv5[21:t - 1]), w(rv22[21:t - 1])])
            y = w(r2[22:t])
            betas_har, *_ = np.linalg.lstsq(X, y, rcond=None)
            try:
                params_gjr = ajustar_gjr(pd.Series(r[:t + 1] * 100))
                sigma2 = params_gjr[4] / 1e4
            except Exception:
                params_gjr = None
            mascara = ~np.isnan(features[21:t - 1]).any(axis=1)
            Xl, yl = features[21:t - 1][mascara], log(w(r2[22:t][mascara]))
            modelo_lgb = lgb.LGBMRegressor(
                n_estimators=200, learning_rate=0.05, num_leaves=15,
                min_child_samples=30, random_state=42, verbose=-1,
            ).fit(Xl, yl)

        pron["HIST21"][t] = rv21[t]
        pron["EWMA"][t] = ewma[t]
        pron["HAR"][t] = np.clip(betas_har[0] + betas_har[1] * r2[t]
                                 + betas_har[2] * rv5[t] + betas_har[3] * rv22[t],
                                 f_min, f_max)
        if params_gjr is not None:
            w, a, g, b, _ = params_gjr
            f = (w + a * (r[t] * 100) ** 2
                 + g * (r[t] * 100) ** 2 * (r[t] < 0) + b * sigma2 * 1e4) / 1e4
            pron["GJR-GARCH"][t] = max(f, PISO)
            sigma2 = max(f, PISO)
        if modelo_lgb is not None and not np.isnan(features[t]).any():
            pron["LightGBM"][t] = float(np.clip(
                np.exp(modelo_lgb.predict(features[[t]])[0]), f_min, f_max))

    return pron, r2


def main():
    print("=" * 70)
    print("   FASE 2: TORNEO DE MODELOS DE PRONOSTICO DE VOLATILIDAD")
    print("=" * 70)

    universo = {}
    for tk in MERCADOS:
        df = preparar_activo(tk, inicio=INICIO, fin=FIN)
        if df is not None:
            universo[tk] = df
    print(f"\n[*] {len(universo)} mercados | modelos: {MODELOS}")

    # Factor global de volatilidad (spillovers): promedio de RV21 entre mercados
    series_rv = {}
    for t, df in universo.items():
        rv = (df["Return"] ** 2).rolling(21).mean()
        series_rv[t] = pd.Series(rv.to_numpy(), index=pd.DatetimeIndex(df["Date"]))
    global_rv = pd.DataFrame(series_rv).mean(axis=1).sort_index().ffill()

    por_mercado = {}
    acumulado = {m: {"sel": [], "sag": []} for m in MODELOS}

    for tk, df in universo.items():
        fechas = pd.DatetimeIndex(df["Date"])
        r = df["Return"].to_numpy(dtype=np.float64)
        factor = global_rv.reindex(fechas).ffill().to_numpy()
        pron, r2 = pronosticos_mercado(r, factor)

        # Evaluación: pronóstico en t se compara con proxy r²(t+1)
        proxy = np.roll(r2, -1)
        validos = ~np.isnan(pron["HAR"])
        validos[-1] = False
        es_sagrado = np.asarray(fechas >= SAGRADA) & validos
        es_sel = validos & ~es_sagrado

        perdidas = {}
        resultado = {"nombre": MERCADOS[tk], "n_pronosticos": int(validos.sum()),
                     "qlike_sel": {}, "qlike_sag": {}, "dm_vs_har": {}}
        for m in MODELOS:
            ok = validos & ~np.isnan(pron[m])
            l = qlike(pron[m], proxy)
            perdidas[m] = l
            sel, sag = ok & es_sel, ok & es_sagrado
            resultado["qlike_sel"][m] = round(float(np.nanmean(l[sel])), 4) if sel.sum() else None
            resultado["qlike_sag"][m] = round(float(np.nanmean(l[sag])), 4) if sag.sum() else None
            if sel.sum():
                acumulado[m]["sel"].append(resultado["qlike_sel"][m])
            if sag.sum():
                acumulado[m]["sag"].append(resultado["qlike_sag"][m])

        for m in MODELOS:
            if m == "HAR":
                continue
            comun = es_sel & ~np.isnan(pron[m]) & ~np.isnan(pron["HAR"])
            stat, p = dm_test(perdidas[m][comun], perdidas["HAR"][comun])
            resultado["dm_vs_har"][m] = {"stat": stat, "p": p}

        validos_sel = {m: v for m, v in resultado["qlike_sel"].items() if v is not None}
        resultado["mejor_sel"] = min(validos_sel, key=validos_sel.get)
        por_mercado[tk] = resultado
        print(f"  {MERCADOS[tk]:<26}: mejor={resultado['mejor_sel']:<9} | "
              f"QLIKE sel: " + " ".join(f"{m}={resultado['qlike_sel'][m]}" for m in MODELOS))

    # ---------------- Agregado global ----------------
    global_json = {}
    for m in MODELOS:
        gana = sum(1 for tk in por_mercado if por_mercado[tk]["mejor_sel"] == m)
        dm_sig = sum(1 for tk in por_mercado
                     if m != "HAR" and por_mercado[tk]["dm_vs_har"].get(m, {}).get("p") is not None
                     and por_mercado[tk]["dm_vs_har"][m]["p"] < 0.05
                     and por_mercado[tk]["qlike_sel"][m] < por_mercado[tk]["qlike_sel"]["HAR"])
        global_json[m] = {
            "qlike_prom_sel": round(float(np.mean(acumulado[m]["sel"])), 4),
            "qlike_prom_sag": round(float(np.mean(acumulado[m]["sag"])), 4),
            "mercados_donde_gana": gana,
            "vence_har_dm_significativo": dm_sig if m != "HAR" else None,
        }

    mejor_global = min(global_json, key=lambda m: global_json[m]["qlike_prom_sel"])
    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metodologia": "Pronóstico de varianza a 1 día (proxy: retorno²), pérdida QLIKE, walk-forward expansivo con re-estimación trimestral, DM vs HAR (Newey-West) en selección (pre-2025-07), sagrado reportado aparte. HAR y LightGBM con winsorización [0.5%, 99.5%] del entrenamiento y pronósticos acotados a rangos de cordura derivados solo del pasado (estabilidad numérica ante outliers tipo abril-2020). Regla pre-registrada: un modelo predice solo si vence a HIST-21 y a HAR con DM p<0.05 en la mayoría de mercados.",
        "modelos": MODELOS,
        "global": global_json,
        "mejor_global": mejor_global,
        "por_mercado": por_mercado,
    }
    os.makedirs(DIR_SALIDA, exist_ok=True)
    with open(f"{DIR_SALIDA}/vol_modelos.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)

    print("\n[GLOBAL] QLIKE promedio (selección, menor = mejor):")
    for m in MODELOS:
        g = global_json[m]
        print(f"  {m:<10}: sel {g['qlike_prom_sel']} | sagrado {g['qlike_prom_sag']} "
              f"| gana en {g['mercados_donde_gana']} mercados"
              + (f" | vence a HAR con DM sig. en {g['vence_har_dm_significativo']}" if m != "HAR" else ""))
    print(f"\n[MEJOR GLOBAL] {mejor_global}")
    print(f"[+] Resultados exportados a {DIR_SALIDA}/vol_modelos.json")


if __name__ == "__main__":
    main()
