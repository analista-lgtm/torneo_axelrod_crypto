"""
Experimento 15: Implementabilidad y robustez del Portafolio Institucional.

El Exp. 14 encontró que la mezcla 25/75 (TSMOM/B&H) maximiza el Sharpe.
Antes de considerarla operable hay que responder cuatro preguntas:

  1. ROBUSTEZ DEL PESO: ¿Sharpe(w) es una meseta o un pico frágil?
     Barrido fino de w (0 a 1, paso 0.05) en la ventana completa Y en la
     ventana de selección (pre-sagrado); el w* elegido solo con selección
     se examina en el período sagrado (elección honesta, sin mirar el
     futuro).
  2. REBALANCEO REALISTA: nadie rebalancea a diario. ¿Qué pierde la
     mezcla con rebalanceo mensual o trimestral entre los dos sleeves?
  3. CRISIS ALPHA: en el peor decil de meses del B&H diversificado,
     ¿cuánto amortigua la mezcla? (el mecanismo económico de la
     diversificación, medido).
  4. COLAS: Sortino, peor mes, peor trimestre, asimetría y % de meses
     positivos de la mezcla institucional.

Salida: data/multi_activo/implementacion.json (se muestra dentro de la
pestaña 🏦 Institucional del dashboard).
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.meta_portfolio import inferencia, metricas
from src.meta_portfolio_v2 import (
    SAGRADA,
    cargar_mercados,
    construir,
    senales_siempre_largo,
)

DIR_SALIDA = "data/multi_activo"
PESOS = [round(w, 2) for w in np.arange(0.0, 1.0001, 0.05)]


def sharpe_de(d, ann=252):
    d = np.asarray(d, dtype=np.float64)
    s = d.std(ddof=1)
    return round(float(np.sqrt(ann) * d.mean() / s), 3) if s > 0 else 0.0


def mezclar_con_rebalanceo(rt, rb, w, frecuencia):
    """Mezcla con dos sleeves que solo se rebalancean al inicio de cada período."""
    if frecuencia == "diario":
        return w * rt + (1 - w) * rb
    periodos = rt.index.to_period("M" if frecuencia == "mensual" else "Q")
    vt, vb = w, 1.0 - w
    valores = np.empty(len(rt))
    arr_t, arr_b = rt.to_numpy(), rb.to_numpy()
    per = periodos.to_numpy()
    for i in range(len(rt)):
        if i > 0 and per[i] != per[i - 1]:
            total = vt + vb
            vt, vb = w * total, (1 - w) * total
        valores[i] = (vt * arr_t[i] + vb * arr_b[i]) / (vt + vb)
        vt *= 1 + arr_t[i]
        vb *= 1 + arr_b[i]
    return pd.Series(valores, index=rt.index)


def main():
    print("=" * 70)
    print("   EXPERIMENTO 15: IMPLEMENTABILIDAD DEL PORTAFOLIO INSTITUCIONAL")
    print("=" * 70)

    b = cargar_mercados()
    tsmom = construir(b, b["senales"]["TSMOM-252 (primaria)"])
    bh = construir(b, senales_siempre_largo(b), con_costos=False)
    comunes = tsmom.index.intersection(bh.index)
    tsmom, bh = tsmom[comunes], bh[comunes]
    sel_t, sel_b = tsmom[tsmom.index < SAGRADA], bh[bh.index < SAGRADA]
    sag_t, sag_b = tsmom[tsmom.index >= SAGRADA], bh[bh.index >= SAGRADA]

    # ---- 1. Robustez del peso ----
    grid_total = [sharpe_de((w * tsmom + (1 - w) * bh).to_numpy()) for w in PESOS]
    grid_sel = [sharpe_de((w * sel_t + (1 - w) * sel_b).to_numpy()) for w in PESOS]
    w_opt_sel = PESOS[int(np.argmax(grid_sel))]
    mezcla_sag = w_opt_sel * sag_t + (1 - w_opt_sel) * sag_b
    print(f"\n[1] w* elegido SOLO con la ventana de selección: {w_opt_sel:.2f}")
    print(f"    Sagrado con w*={w_opt_sel:.2f}: {metricas(mezcla_sag.to_numpy())}")
    meseta = [PESOS[i] for i, s in enumerate(grid_total) if s >= max(grid_total) - 0.05]
    print(f"    Meseta de Sharpe (a menos de 0.05 del maximo): w en [{min(meseta)}, {max(meseta)}]")

    # ---- 2. Rebalanceo realista (con el w* honesto) ----
    rebalanceo = {}
    for frec in ["diario", "mensual", "trimestral"]:
        m = mezclar_con_rebalanceo(tsmom, bh, w_opt_sel, frec)
        rebalanceo[frec] = {**metricas(m.to_numpy()), "t_stat": inferencia(m.to_numpy())["t_stat"]}
        print(f"[2] Rebalanceo {frec:<11}: {rebalanceo[frec]}")

    # ---- 3. Crisis alpha: peor decil de meses del B&H ----
    mes_bh = (1 + bh).resample("ME").prod() - 1
    mes_t = (1 + tsmom).resample("ME").prod() - 1
    mezcla = w_opt_sel * tsmom + (1 - w_opt_sel) * bh
    mes_mix = (1 + mezcla).resample("ME").prod() - 1
    umbral = mes_bh.quantile(0.10)
    crisis = mes_bh[mes_bh <= umbral].index
    crisis_stats = {
        "num_meses_crisis": int(len(crisis)),
        "umbral_decil_pct": round(float(umbral) * 100, 2),
        "bh_prom_pct": round(float(mes_bh[crisis].mean()) * 100, 2),
        "tsmom_prom_pct": round(float(mes_t[crisis].mean()) * 100, 2),
        "mezcla_prom_pct": round(float(mes_mix[crisis].mean()) * 100, 2),
    }
    print(f"[3] Crisis (peor decil B&H, {crisis_stats['num_meses_crisis']} meses): "
          f"B&H {crisis_stats['bh_prom_pct']}% | TSMOM {crisis_stats['tsmom_prom_pct']}% "
          f"| mezcla {crisis_stats['mezcla_prom_pct']}%")

    # ---- 4. Colas de la mezcla institucional ----
    d = mezcla.to_numpy()
    negativo = np.minimum(d, 0.0)
    downside = np.sqrt((negativo ** 2).mean())
    trimestre = (1 + mezcla).resample("QE").prod() - 1
    colas = {
        "sortino": round(float(np.sqrt(252) * d.mean() / downside), 2) if downside > 0 else None,
        "peor_mes_pct": round(float(mes_mix.min()) * 100, 2),
        "peor_trimestre_pct": round(float(trimestre.min()) * 100, 2),
        "asimetria": round(float(pd.Series(d).skew()), 2),
        "pct_meses_positivos": round(float((mes_mix > 0).mean()) * 100, 1),
    }
    print(f"[4] Colas de la mezcla w*={w_opt_sel:.2f}: {colas}")

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sagrada_desde": SAGRADA,
        "grid": {"pesos": PESOS, "sharpe_total": grid_total, "sharpe_seleccion": grid_sel},
        "w_optimo_seleccion": w_opt_sel,
        "meseta": {"desde": min(meseta), "hasta": max(meseta)},
        "sagrado_con_w_optimo": metricas(mezcla_sag.to_numpy()),
        "rebalanceo": rebalanceo,
        "crisis": crisis_stats,
        "colas": colas,
    }
    os.makedirs(DIR_SALIDA, exist_ok=True)
    with open(f"{DIR_SALIDA}/implementacion.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    print(f"\n[+] Resultados exportados a {DIR_SALIDA}/implementacion.json")


if __name__ == "__main__":
    main()
