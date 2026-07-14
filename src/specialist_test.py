"""
Experimento 9: La Prueba del Especialista.

Hipótesis del usuario (legítima): los mercados son distintos por naturaleza
y una estrategia puede ser rentable solo en el suyo — una especialista de
BTC no tiene por qué funcionar en divisas.

Lo que la hipótesis NO elimina es la prueba temporal: la especialista de
BTC debe seguir funcionando en el BTC del futuro. Este experimento evalúa
exactamente eso, mercado por mercado y sin exigencia cruzada:

  Para cada mercado (11: los 6 originales + los 5 vírgenes),
  cada representación (secuencia diaria N=4 y régimen) y cada corte:
    - Campeonas locales del train: retorno > Buy & Hold del train.
    - Éxito en test: retorno > Buy & Hold del test (ganarle a SU mercado).
    - Lift: tasa de éxito de las campeonas vs. tasa base de TODAS.
    - Spearman(train, test): correlación de rangos de las 65,536
      estrategias entre períodos. Si existe memoria explotable en el
      mercado, el ranking debe persistir (> 0); si es ruido, ~0;
      si es reversión, < 0.

Salida: data/multi_activo/especialistas.json (pestaña 🎯 del dashboard).
"""
import json
import os
from datetime import datetime, timezone

import numpy as np

from src.data_pipeline import ACTIVOS, preparar_activo, cargar_universo
from src.representation_lab import CORTES, censo_retornos
from src.representations import rep_regimen, rep_secuencia_n4

DIR_SALIDA = "data/multi_activo"
N_ESTADOS = 16
TOTAL = 2 ** N_ESTADOS
MIN_TRAIN, MIN_TEST = 80, 40

MERCADOS_EXTRA = {
    "TLT": "Bonos Tesoro 20+ años",
    "EEM": "Mercados Emergentes",
    "^N225": "Nikkei 225 (Japón)",
    "SI=F": "Plata (Futuros)",
    "USDJPY=X": "Dólar/Yen",
}

REPS = {
    "secuencia_n4": {"nombre": "Secuencia diaria N=4", "fn": rep_secuencia_n4},
    "regimen": {"nombre": "Régimen (SMA + volatilidad)", "fn": rep_regimen},
}


def spearman(a, b):
    """Correlación de Spearman vía doble argsort (sin dependencias extra)."""
    ra = np.argsort(np.argsort(a)).astype(np.float64)
    rb = np.argsort(np.argsort(b)).astype(np.float64)
    return float(np.corrcoef(ra, rb)[0, 1])


def main():
    print("=" * 70)
    print("   EXPERIMENTO 9: LA PRUEBA DEL ESPECIALISTA (11 MERCADOS)")
    print("=" * 70)

    universo = cargar_universo()
    nombres = {t: ACTIVOS[t]["nombre"] for t in universo}
    for tk, nombre in MERCADOS_EXTRA.items():
        df = preparar_activo(tk)
        if df is not None:
            universo[tk] = df
            nombres[tk] = nombre

    mercados_json = {}
    lifts_globales, rhos_globales = [], []

    for tk, df in universo.items():
        detalle = []
        for rep_id, rep in REPS.items():
            serie = rep["fn"](df)
            for corte in CORTES:
                tr = serie[serie["Date"] < corte]
                te = serie[serie["Date"] >= corte]
                if len(tr) < MIN_TRAIN or len(te) < MIN_TEST:
                    continue
                r_tr = censo_retornos(tr["Code"].to_numpy(),
                                      tr["Next_Return"].to_numpy(dtype=np.float64), N_ESTADOS)
                r_te = censo_retornos(te["Code"].to_numpy(),
                                      te["Next_Return"].to_numpy(dtype=np.float64), N_ESTADOS)
                bh_tr, bh_te = r_tr[TOTAL - 1], r_te[TOTAL - 1]   # siempre-Long = B&H

                campeonas = r_tr > bh_tr
                exito = r_te > bh_te
                base = float(exito.mean())
                tasa = float(exito[campeonas].mean()) if campeonas.sum() > 0 else None
                lift = round(tasa / base, 2) if (tasa is not None and base > 0) else None
                rho = round(spearman(r_tr, r_te), 3)

                detalle.append(
                    {
                        "rep": rep_id,
                        "corte": corte,
                        "campeonas": int(campeonas.sum()),
                        "exito_campeonas_pct": round((tasa or 0) * 100, 2) if tasa is not None else None,
                        "base_pct": round(base * 100, 2),
                        "lift": lift,
                        "spearman": rho,
                    }
                )

        lifts = [x["lift"] for x in detalle if x["lift"] is not None]
        rhos = [x["spearman"] for x in detalle]
        lifts_globales += lifts
        rhos_globales += rhos
        mercados_json[tk] = {
            "nombre": nombres[tk],
            "lift_promedio": round(float(np.mean(lifts)), 2) if lifts else None,
            "spearman_promedio": round(float(np.mean(rhos)), 3) if rhos else None,
            "detalle": detalle,
        }
        print(f"  {nombres[tk]:<24}: lift promedio "
              f"{mercados_json[tk]['lift_promedio']} | spearman promedio "
              f"{mercados_json[tk]['spearman_promedio']}")

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "criterio": "Campeonas del train (retorno > B&H train) evaluadas en su PROPIO mercado en test (retorno > B&H test), sin exigencia cruzada",
        "cortes": CORTES,
        "representaciones": {k: v["nombre"] for k, v in REPS.items()},
        "global": {
            "lift_promedio": round(float(np.mean(lifts_globales)), 2),
            "spearman_promedio": round(float(np.mean(rhos_globales)), 3),
        },
        "mercados": mercados_json,
    }
    os.makedirs(DIR_SALIDA, exist_ok=True)
    with open(f"{DIR_SALIDA}/especialistas.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    print(f"\n[GLOBAL] lift promedio: {salida['global']['lift_promedio']} | "
          f"spearman promedio: {salida['global']['spearman_promedio']}")
    print(f"[+] Resultados exportados a {DIR_SALIDA}/especialistas.json")


if __name__ == "__main__":
    main()
