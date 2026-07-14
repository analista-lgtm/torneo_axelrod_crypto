"""
Experimento 6: Validación Walk-Forward (overfitting en la variable tiempo).

La robustez cruzada entre activos (Experimento 5) no garantiza robustez
temporal: la élite podría estar capturando una lógica exclusiva de la
ventana 2021-2026 completa. Esta prueba separa la historia en dos mitades
que nunca se mezclan:

  TRAIN (selección): 2021-07-01 -> 2024-06-30
  TEST  (validación): 2024-07-01 -> 2026-07-01

La élite universal se selecciona usando ÚNICAMENTE el período train
(retorno > 0 en los 6 activos) y luego se evalúa en el período test,
que la selección jamás vio.

Métrica clave — el LIFT: compara la tasa de supervivencia de la élite
train en el test contra la tasa base (qué fracción de TODAS las
estrategias resulta universal en el test por simple azar/mercado).
  lift ≈ 1  -> la élite no es mejor que el azar (overfitting temporal)
  lift >> 1 -> la selección train contiene señal que persiste en el tiempo

Salida: data/multi_activo/walkforward.json (consumida por el dashboard).
"""
import json
import os
from datetime import datetime, timezone

import numpy as np

from src.data_pipeline import cargar_universo
from src.multi_asset_tournament import (
    EXPERIMENTOS,
    MODOS,
    adn_de_ids,
    consenso_y_familias,
    UMBRAL_HAMMING,
)

DIR_SALIDA = "data/multi_activo"
CORTE = "2024-07-01"
TOP_DETALLE = 20
CHUNK = 8192


def censo_retorno_total(df, columna, n_estados, corto):
    """Retorno total (%) de las 2^n_estados estrategias (sin curva de equity)."""
    estados = df[columna].to_numpy()
    rets = df["Next_Return"].to_numpy(dtype=np.float64)
    total = 2 ** n_estados
    out = np.empty(total)
    for i0 in range(0, total, CHUNK):
        ids = np.arange(i0, min(i0 + CHUNK, total))
        acciones = np.where(adn_de_ids(ids, n_estados) == 1, 1, corto)
        out[ids] = (np.prod(1.0 + acciones[:, estados] * rets[None, :], axis=1) - 1.0) * 100
    return out


def main():
    print("=" * 70)
    print("   EXPERIMENTO 6: VALIDACIÓN WALK-FORWARD (TRAIN 21-24 / TEST 24-26)")
    print("=" * 70)

    universo = cargar_universo()
    tickers = list(universo.keys())

    train, test = {}, {}
    ventanas = {"train": {}, "test": {}}
    for t in tickers:
        df = universo[t]
        train[t] = df[df["Date"] < CORTE].copy()
        test[t] = df[df["Date"] >= CORTE].copy()
        ventanas["train"][t] = {"velas": int(len(train[t])),
                                "fin": str(train[t]["Date"].iloc[-1].date())}
        ventanas["test"][t] = {"velas": int(len(test[t])),
                               "inicio": str(test[t]["Date"].iloc[0].date())}
        print(f"[SPLIT] {t:<9}: train {len(train[t]):>5} velas | test {len(test[t]):>5} velas")

    resultados = {}
    for exp_id, cfg in EXPERIMENTOS.items():
        n_estados = cfg["estados"]
        total = 2 ** n_estados
        resultados[exp_id] = {}

        for modo_id, modo in MODOS.items():
            print(f"\n[{exp_id}·{modo_id}] Censos train/test de {total:,} estrategias...")
            ret_train = {t: censo_retorno_total(train[t], cfg["columna"], n_estados, modo["corto"])
                         for t in tickers}
            ret_test = {t: censo_retorno_total(test[t], cfg["columna"], n_estados, modo["corto"])
                        for t in tickers}

            m_train = np.stack([ret_train[t] for t in tickers])
            m_test = np.stack([ret_test[t] for t in tickers])
            min_train = m_train.min(axis=0)
            min_test = m_test.min(axis=0)

            uni_train = np.all(m_train > 0, axis=0)          # élite seleccionada SOLO con train
            uni_test = np.all(m_test > 0, axis=0)            # universales del test (referencia)
            sobreviven = uni_train & uni_test

            n_train = int(uni_train.sum())
            base_rate = float(uni_test.mean())               # tasa base de azar en test
            pct_sup = float(sobreviven.sum() / n_train) if n_train > 0 else None
            lift = (pct_sup / base_rate) if (n_train > 0 and base_rate > 0) else None

            ids_train = np.where(uni_train)[0]
            ids_train = ids_train[np.argsort(-min_train[ids_train])]

            consenso, _ = consenso_y_familias(ids_train[:200], n_estados, UMBRAL_HAMMING[exp_id])

            detalle = [
                {
                    "ADN": format(int(i), f"0{n_estados}b"),
                    "min_train": round(float(min_train[i]), 2),
                    "min_test": round(float(min_test[i]), 2),
                    "sobrevive": bool(uni_test[i]),
                    "retornos_test": {t: round(float(ret_test[t][i]), 2) for t in tickers},
                }
                for i in ids_train[:TOP_DETALLE]
            ]

            resultados[exp_id][modo_id] = {
                "train_universales": n_train,
                "base_rate_test_pct": round(base_rate * 100, 3),
                "sobreviven": int(sobreviven.sum()),
                "pct_supervivencia": round(pct_sup * 100, 2) if pct_sup is not None else None,
                "lift": round(lift, 2) if lift is not None else None,
                "mediana_min_test_elite": round(float(np.median(min_test[ids_train])), 2)
                if n_train > 0 else None,
                "mediana_min_test_todas": round(float(np.median(min_test)), 2),
                "consenso_train": consenso,
                "top": detalle,
            }
            print(f"  Train-universales: {n_train:,} | sobreviven en test: {int(sobreviven.sum()):,} "
                  f"({resultados[exp_id][modo_id]['pct_supervivencia']}%) | "
                  f"tasa base: {round(base_rate * 100, 3)}% | lift: {resultados[exp_id][modo_id]['lift']}")

    os.makedirs(DIR_SALIDA, exist_ok=True)
    with open(f"{DIR_SALIDA}/walkforward.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "corte": CORTE,
                "interpretacion": "lift ~1: la élite train no supera al azar en el test (overfitting temporal). lift >> 1: la selección contiene señal que persiste en el tiempo.",
                "ventanas": ventanas,
                "resultados": resultados,
            },
            f, ensure_ascii=False,
        )
    print(f"\n[+] Resultados exportados a {DIR_SALIDA}/walkforward.json")


if __name__ == "__main__":
    main()
