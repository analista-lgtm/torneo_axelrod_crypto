"""
Fase 1.5: Laboratorio de Representaciones.

Somete cada codificación del mercado (src/representations.py) al tribunal
completo de robustez, en modo Long/Short (el detector más exigente):

  Para cada CORTE temporal (4 fechas distintas):
    1. Élite universal en el train (retorno > 0 en los 6 activos).
    2. Supervivencia de esa élite en el test (retorno > 0 en los 6).
    3. Lift vs. la tasa base del azar en ese test.

  Veredicto por representación:
    - lift promedio entre cortes (persistencia media)
    - "supervivientes totales": estrategias que son universales en train
      Y test en TODOS los cortes a la vez — las candidatas reales.

Usar múltiples cortes evita que una fecha de división afortunada produzca
un falso positivo: una representación robusta debe funcionar sin importar
dónde se corte la historia.

Salida: data/multi_activo/representaciones.json (pestaña 🔬 del dashboard).
"""
import json
import os
from datetime import datetime, timezone

import numpy as np

from src.data_pipeline import cargar_universo
from src.multi_asset_tournament import adn_de_ids
from src.representations import REPRESENTACIONES

DIR_SALIDA = "data/multi_activo"
CORTES = ["2023-07-01", "2024-01-01", "2024-07-01", "2025-01-01"]
CORTO = -1                    # modo Long/Short: el detector estricto
MIN_TRAIN, MIN_TEST = 80, 40  # velas mínimas por sub-período
TOP_SUPERVIVIENTES = 20
CHUNK = 8192


def censo_retornos(estados, rets, n_estados, corto=CORTO):
    """Retorno total (%) de todas las estrategias sobre arrays ya preparados."""
    total = 2 ** n_estados
    out = np.empty(total)
    for i0 in range(0, total, CHUNK):
        ids = np.arange(i0, min(i0 + CHUNK, total))
        acciones = np.where(adn_de_ids(ids, n_estados) == 1, 1, corto)
        out[ids] = (np.prod(1.0 + acciones[:, estados] * rets[None, :], axis=1) - 1.0) * 100
    return out


def main():
    print("=" * 70)
    print("   FASE 1.5: LABORATORIO DE REPRESENTACIONES (WALK-FORWARD x4)")
    print("=" * 70)

    universo = cargar_universo()
    tickers = list(universo.keys())

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modo": "Long/Short (detector estricto)",
        "cortes": CORTES,
        "criterio_final": "Universal en train Y test en TODOS los cortes simultáneamente",
        "representaciones": {},
    }

    for rep_id, rep in REPRESENTACIONES.items():
        n_estados = rep["n_estados"]
        total = 2 ** n_estados
        print(f"\n[{rep_id}] {rep['nombre']} ({total:,} estrategias)")

        # Transformar cada activo con la representación (una sola vez)
        series = {}
        ok = True
        for t in tickers:
            d = rep["fn"](universo[t])
            if d["Code"].max() >= n_estados or d["Code"].min() < 0:
                print(f"  [-] Códigos fuera de rango en {t}. Representación descartada.")
                ok = False
                break
            series[t] = d
        if not ok:
            continue

        resultados_cortes = []
        aprobados_global = np.ones(total, dtype=bool)   # supervivientes en TODOS los cortes
        ret_full = {t: censo_retornos(series[t]["Code"].to_numpy(),
                                      series[t]["Next_Return"].to_numpy(dtype=np.float64),
                                      n_estados)
                    for t in tickers}

        for corte in CORTES:
            m_train, m_test = [], []
            velas_ok = True
            for t in tickers:
                d = series[t]
                tr = d[d["Date"] < corte]
                te = d[d["Date"] >= corte]
                if len(tr) < MIN_TRAIN or len(te) < MIN_TEST:
                    velas_ok = False
                    break
                m_train.append(censo_retornos(tr["Code"].to_numpy(),
                                              tr["Next_Return"].to_numpy(dtype=np.float64), n_estados))
                m_test.append(censo_retornos(te["Code"].to_numpy(),
                                             te["Next_Return"].to_numpy(dtype=np.float64), n_estados))
            if not velas_ok:
                resultados_cortes.append({"corte": corte, "valido": False})
                print(f"  corte {corte}: datos insuficientes, omitido")
                continue

            m_train = np.stack(m_train)
            m_test = np.stack(m_test)
            uni_train = np.all(m_train > 0, axis=0)
            uni_test = np.all(m_test > 0, axis=0)
            sobreviven = uni_train & uni_test
            aprobados_global &= sobreviven

            n_tr = int(uni_train.sum())
            base = float(uni_test.mean())
            pct_sup = float(sobreviven.sum() / n_tr) if n_tr > 0 else None
            lift = round(pct_sup / base, 2) if (n_tr > 0 and base > 0) else None
            resultados_cortes.append(
                {
                    "corte": corte,
                    "valido": True,
                    "train_universales": n_tr,
                    "sobreviven": int(sobreviven.sum()),
                    "base_rate_pct": round(base * 100, 3),
                    "pct_supervivencia": round(pct_sup * 100, 2) if pct_sup is not None else None,
                    "lift": lift,
                }
            )
            print(f"  corte {corte}: train-uni {n_tr:,} -> sobreviven {int(sobreviven.sum()):,} "
                  f"| base {round(base * 100, 3)}% | lift {lift}")

        lifts = [c["lift"] for c in resultados_cortes if c.get("valido") and c["lift"] is not None]
        ids_finales = np.where(aprobados_global)[0]
        min_full = np.min(np.stack([ret_full[t] for t in tickers]), axis=0)
        if len(ids_finales) > 0:
            ids_finales = ids_finales[np.argsort(-min_full[ids_finales])]

        supervivientes = [
            {
                "ID": int(i),
                "ADN": format(int(i), f"0{n_estados}b"),
                "retornos": {t: round(float(ret_full[t][i]), 2) for t in tickers},
                "min": round(float(min_full[i]), 2),
            }
            for i in ids_finales[:TOP_SUPERVIVIENTES]
        ]

        salida["representaciones"][rep_id] = {
            "nombre": rep["nombre"],
            "hipotesis": rep["hipotesis"],
            "n_estados": n_estados,
            "total_estrategias": total,
            "cortes": resultados_cortes,
            "lift_promedio": round(float(np.mean(lifts)), 2) if lifts else None,
            "supervivientes_totales": int(len(ids_finales)),
            "supervivientes": supervivientes,
        }
        print(f"  ==> lift promedio: {salida['representaciones'][rep_id]['lift_promedio']} "
              f"| supervivientes en TODOS los cortes: {len(ids_finales):,}")

    os.makedirs(DIR_SALIDA, exist_ok=True)
    with open(f"{DIR_SALIDA}/representaciones.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    print(f"\n[+] Resultados exportados a {DIR_SALIDA}/representaciones.json")


if __name__ == "__main__":
    main()
