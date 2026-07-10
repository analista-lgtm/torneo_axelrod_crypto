"""
Experimento 16 (Fase 3): el termostato anticipativo.

El portafolio institucional 40/60 escala su exposición con vol-targeting
basado en la volatilidad rodante de 63 días — un estimador REACTIVO (mira
atrás). La Fase 2 coronó al GJR-GARCH como mejor pronosticador de varianza
(y a EWMA como subcampeón barato). Este experimento responde la pregunta
de integración: ¿un termostato ANTICIPATIVO mejora el portafolio?

Tres variantes del MISMO portafolio 40/60 (idénticas señales, pesos y
costos; solo cambia el estimador de vol del targeting, aplicado a cada
componente antes de mezclar, como en los Exps. 14-15):

  A. Rodante-63d (statu quo, Exps. 13-15).
  B. GJR-GARCH: pronóstico a 1 día de la varianza del componente,
     walk-forward con re-ajuste trimestral (recursión causal entre
     ajustes; EWMA de respaldo si el ajuste falla).
  C. EWMA (RiskMetrics λ=0.94), rezagada 1 día.

Inferencia: métricas en la muestra común (todas las variantes definidas),
período sagrado aparte, y bootstrap por bloques PAREADO (mismos índices
para ambas series) de la diferencia de Sharpe B−A y C−A, con p-valor de
que la mejora sea ≤ 0.

Salida: data/multi_activo/vol_target_v3.json (pestaña 🌡️ del dashboard).
"""
import json
import os
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.meta_portfolio import metricas, inferencia
from src.meta_portfolio_v2 import (
    LEV_MAX,
    SAGRADA,
    VOL_OBJETIVO_ANUAL,
    cargar_mercados,
    construir_base,
    senales_siempre_largo,
    vol_target_rodante,
)

warnings.filterwarnings("ignore")

DIR_SALIDA = "data/multi_activo"
W_TSMOM = 0.40
WARMUP = 504
REFIT = 63
LAMBDA_EWMA = 0.94
BLOQUE, N_BOOT, SEMILLA = 10, 2000, 42
VOL_DIARIA_OBJ = VOL_OBJETIVO_ANUAL / np.sqrt(252)


def prevision_gjr(base):
    """Varianza prevista para la fila t con información <= t-1 (walk-forward)."""
    from arch import arch_model
    r = base.to_numpy()
    n = len(r)
    prev = np.full(n, np.nan)
    ewma = pd.Series(r ** 2).ewm(alpha=1 - LAMBDA_EWMA).mean().shift(1).to_numpy()
    params, sigma2 = None, None
    for t in range(WARMUP, n):
        if (t - WARMUP) % REFIT == 0:
            try:
                am = arch_model(pd.Series(r[:t] * 100), mean="Zero",
                                vol="GARCH", p=1, o=1, q=1, rescale=False)
                res = am.fit(disp="off", show_warning=False)
                p = res.params
                params = (float(p["omega"]), float(p["alpha[1]"]),
                          float(p["gamma[1]"]), float(p["beta[1]"]))
                sigma2 = float(res.conditional_volatility.iloc[-1] ** 2)
            except Exception:
                params = None
        if params is not None:
            w, a, g, bcoef = params
            # sigma2 pronostica la fila t usando el retorno de t-1
            f = w + a * (r[t - 1] * 100) ** 2 + g * (r[t - 1] * 100) ** 2 * (r[t - 1] < 0) + bcoef * sigma2
            sigma2 = max(f, 1e-8)
            prev[t] = sigma2 / 1e4
        else:
            prev[t] = ewma[t]
    return pd.Series(prev, index=base.index)


def aplicar_target(base, var_prevista):
    lev = (VOL_DIARIA_OBJ / np.sqrt(var_prevista)).clip(upper=LEV_MAX)
    return (lev * base).dropna()


def sharpe(d, ann=252):
    s = d.std(ddof=1)
    return float(np.sqrt(ann) * d.mean() / s) if s > 0 else 0.0


def bootstrap_pareado(a, b):
    """P-valor de que Sharpe(b) - Sharpe(a) <= 0, con bloques idénticos."""
    n = len(a)
    rng = np.random.default_rng(SEMILLA)
    n_bloques = int(np.ceil(n / BLOQUE))
    difs = []
    for _ in range(N_BOOT):
        inicios = rng.integers(0, n - BLOQUE + 1, n_bloques)
        idx = np.concatenate([np.arange(i, i + BLOQUE) for i in inicios])[:n]
        difs.append(sharpe(b[idx]) - sharpe(a[idx]))
    difs = np.array(difs)
    return round(float((difs <= 0).mean()), 4), round(float(np.median(difs)), 3)


def main():
    print("=" * 70)
    print("   EXPERIMENTO 16: TERMOSTATO ANTICIPATIVO (VOL-TARGET GJR vs RODANTE)")
    print("=" * 70)

    b = cargar_mercados()
    print(f"\n[*] {len(b['mercados'])} mercados | mezcla {int(W_TSMOM*100)}/{int((1-W_TSMOM)*100)}")

    base_t = construir_base(b, b["senales"]["TSMOM-252 (primaria)"])
    base_b = construir_base(b, senales_siempre_largo(b), con_costos=False)

    print("[*] Ajustando GJR-GARCH walk-forward sobre cada componente...")
    variantes = {}
    componentes = {}
    for nombre, base in [("tsmom", base_t), ("bh", base_b)]:
        ewma_var = (base ** 2).ewm(alpha=1 - LAMBDA_EWMA).mean().shift(1)
        componentes[nombre] = {
            "A": vol_target_rodante(base),
            "B": aplicar_target(base, prevision_gjr(base)),
            "C": aplicar_target(base, ewma_var),
        }

    ETIQUETAS = {"A": "Rodante 63d (statu quo)", "B": "GJR-GARCH (anticipativo)", "C": "EWMA (anticipativo simple)"}
    mezclas = {}
    for v in ETIQUETAS:
        comunes = componentes["tsmom"][v].index.intersection(componentes["bh"][v].index)
        mezclas[v] = W_TSMOM * componentes["tsmom"][v][comunes] + (1 - W_TSMOM) * componentes["bh"][v][comunes]

    # Muestra común: donde TODAS las variantes están definidas
    idx = mezclas["A"].index
    for v in mezclas:
        idx = idx.intersection(mezclas[v].index)
    mezclas = {v: m[idx] for v, m in mezclas.items()}
    print(f"[*] Muestra común: {len(idx)} días ({idx[0].date()} -> {idx[-1].date()})")

    resultados = {}
    for v, etiqueta in ETIQUETAS.items():
        d = mezclas[v].to_numpy()
        sag = mezclas[v][mezclas[v].index >= SAGRADA].to_numpy()
        resultados[v] = {
            "etiqueta": etiqueta,
            "total": metricas(d),
            "inferencia": inferencia(d),
            "sagrado": metricas(sag),
        }
        print(f"  {etiqueta:<28}: {resultados[v]['total']} | sagrado {resultados[v]['sagrado']['retorno']}%")

    a = mezclas["A"].to_numpy()
    for v in ("B", "C"):
        p, mediana = bootstrap_pareado(a, mezclas[v].to_numpy())
        resultados[v]["vs_statu_quo"] = {
            "delta_sharpe": round(resultados[v]["total"]["sharpe"] - resultados["A"]["total"]["sharpe"], 3),
            "delta_sharpe_boot_mediana": mediana,
            "p_mejora": p,
        }
        print(f"  {ETIQUETAS[v]} vs statu quo: dSharpe {resultados[v]['vs_statu_quo']['delta_sharpe']} "
              f"| p(mejora<=0) {p}")

    curvas = {}
    for v, m in mezclas.items():
        eq = (1 + m).cumprod().resample("ME").last().dropna()
        curvas[ETIQUETAS[v]] = {"labels": [x.strftime("%Y-%m") for x in eq.index],
                                "valores": [round(float(x), 4) for x in eq]}

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metodologia": f"Mismo portafolio 40/60 (señales, pesos y costos idénticos); solo cambia el estimador del vol-targeting por componente. GJR walk-forward (warmup {WARMUP}, refit {REFIT}) con recursión causal; muestra común a las 3 variantes; bootstrap pareado por bloques de {BLOQUE}d ({N_BOOT} remuestreos) para la diferencia de Sharpe.",
        "muestra": {"dias": int(len(idx)), "desde": str(idx[0].date()), "hasta": str(idx[-1].date())},
        "sagrada_desde": SAGRADA,
        "variantes": resultados,
        "curvas": curvas,
    }
    os.makedirs(DIR_SALIDA, exist_ok=True)
    with open(f"{DIR_SALIDA}/vol_target_v3.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    print(f"\n[+] Resultados exportados a {DIR_SALIDA}/vol_target_v3.json")


if __name__ == "__main__":
    main()
