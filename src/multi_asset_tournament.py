"""
Torneo Axelrod Multi-Activo: los 3 experimentos (N=2, N=3, N=4) ejecutados
de forma independiente sobre CADA activo del universo, más las dos capas
de auditoría anti-overfitting:

  PASO 1 - Torneo por activo: censo completo de todas las estrategias
           (16, 256 y 65,536) en cada mercado, en modo Long/Short (+1/-1).
  PASO 2 - Pool anti-overfitting por activo: de las campeonas de cada
           torneo local (superan Buy & Hold con Sharpe > 0), cuáles
           mantienen retorno positivo en TODOS los demás activos.
  PASO 3 - Élite universal convergente: estrategias con retorno positivo
           en TODOS los activos a la vez, con análisis de similitud
           (ADN de consenso por estado y familias por distancia de Hamming).

Convención de identidad de estrategias (canónica en todo el proyecto):
  El ADN es una cadena binaria donde la posición s indica la acción para el
  estado de mercado con código s ('1' = Long, '0' = Short). El ID es la
  lectura decimal del ADN (bit más significativo = estado 0). Coincide con
  la columna "Logica" de los experimentos históricos de tournament.py.

Salidas (consumidas por el dashboard index.html): data/multi_activo/*.json
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.data_pipeline import (
    ACTIVOS,
    FACTORES_ANUALIZACION,
    VENTANA_FIN,
    VENTANA_INICIO,
    cargar_universo,
)

DIR_SALIDA = "data/multi_activo"

# Los 3 experimentos: memoria de N días -> 2^N estados -> 2^(2^N) estrategias
EXPERIMENTOS = {
    "N2": {"memoria": 2, "estados": 4, "columna": "Code_N2"},
    "N3": {"memoria": 3, "estados": 8, "columna": "Code_N3"},
    "N4": {"memoria": 4, "estados": 16, "columna": "Code_N4"},
}

TOP_TABLA = 100          # filas exportadas al dashboard por torneo
TOP_POOL = 50            # filas exportadas por pool anti-overfitting
TOP_ELITE = 50           # filas exportadas de la élite universal
UMBRAL_HAMMING = {"N2": 1, "N3": 1, "N4": 2}  # distancia máxima intra-familia
CHUNK = 4096             # estrategias por bloque en el censo vectorizado


def adn_de_ids(ids, n_estados):
    """Matriz (len(ids), n_estados) de bits: posición s = acción del estado s."""
    desplaz = (n_estados - 1) - np.arange(n_estados)
    return (ids[:, None] >> desplaz[None, :]) & 1


def censo_activo(df, columna_estado, n_estados, ann_factor):
    """
    Censo vectorizado de las 2^n_estados estrategias sobre un activo.
    Devuelve arrays (total,) de retorno total (%), Sharpe anualizado y
    máximo drawdown (%), en modo Long/Short: bit 1 = +1, bit 0 = -1.
    """
    estados = df[columna_estado].to_numpy()
    retornos = df["Next_Return"].to_numpy(dtype=np.float64)
    total = 2 ** n_estados

    ret_total = np.empty(total)
    sharpe = np.empty(total)
    max_dd = np.empty(total)

    for inicio in range(0, total, CHUNK):
        ids = np.arange(inicio, min(inicio + CHUNK, total))
        acciones = 2 * adn_de_ids(ids, n_estados) - 1          # bits -> +1/-1
        diarios = acciones[:, estados] * retornos[None, :]      # (chunk, T)
        equity = np.cumprod(1.0 + diarios, axis=1)

        ret_total[ids] = (equity[:, -1] - 1.0) * 100
        media = diarios.mean(axis=1)
        desv = diarios.std(axis=1, ddof=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            sh = np.sqrt(ann_factor) * media / desv
        sharpe[ids] = np.where(desv > 0, sh, 0.0)

        pico = np.maximum.accumulate(equity, axis=1)
        max_dd[ids] = (equity / pico - 1.0).min(axis=1) * 100

    # Validación interna: la estrategia "todo unos" (siempre Long) debe
    # replicar exactamente el retorno compuesto del mercado (Buy & Hold).
    bh = (np.prod(1.0 + retornos) - 1.0) * 100
    assert np.isclose(ret_total[total - 1], bh, rtol=1e-9), \
        f"Inconsistencia en el censo: siempre-Long={ret_total[total - 1]} vs B&H={bh}"

    return ret_total, sharpe, max_dd


def formato_adn(ids, n_estados):
    return [format(int(i), f"0{n_estados}b") for i in np.atleast_1d(ids)]


def fila_metricas(idx, adn, ret, sh, dd):
    return {
        "ID": int(idx),
        "ADN": adn,
        "Retorno": round(float(ret), 2),
        "Sharpe": round(float(sh), 2),
        "Max_DD": round(float(dd), 2),
    }


def consenso_y_familias(ids_elite, n_estados, umbral):
    """ADN de consenso (% Long por estado) y familias por distancia de Hamming."""
    if len(ids_elite) == 0:
        return [], []

    bits = adn_de_ids(np.asarray(ids_elite), n_estados)
    pct_long = bits.mean(axis=0)
    bits_patron = (n_estados - 1).bit_length()
    consenso = [
        {
            "estado": s,
            "patron": format(s, f"0{bits_patron}b"),
            "pct_long": round(float(pct_long[s]) * 100, 1),
        }
        for s in range(n_estados)
    ]

    # Agrupación codiciosa: el mejor no asignado funda una familia y absorbe
    # a todas las estrategias a <= umbral bits de distancia.
    familias = []
    restantes = list(range(len(ids_elite)))
    while restantes:
        rep = restantes.pop(0)
        miembros = [rep]
        aun = []
        for j in restantes:
            if int((bits[rep] != bits[j]).sum()) <= umbral:
                miembros.append(j)
            else:
                aun.append(j)
        restantes = aun
        familias.append(
            {
                "representante": "".join(map(str, bits[rep])),
                "miembros": len(miembros),
                "adn": ["".join(map(str, bits[m])) for m in miembros[:10]],
            }
        )
    return consenso, familias


def main():
    print("=" * 70)
    print("   TORNEO AXELROD MULTI-ACTIVO: CENSO, ANTI-OVERFITTING Y ÉLITE")
    print("=" * 70)

    universo = cargar_universo()
    if len(universo) < 2:
        print("[-] Universo insuficiente para validación cruzada. Abortando.")
        return
    tickers = list(universo.keys())
    os.makedirs(DIR_SALIDA, exist_ok=True)

    # Metadatos y línea base Buy & Hold por activo
    resumen_activos = []
    bh_por_activo = {}
    for t in tickers:
        df = universo[t]
        bh = (np.prod(1.0 + df["Next_Return"].to_numpy()) - 1.0) * 100
        bh_por_activo[t] = bh
        resumen_activos.append(
            {
                "ticker": t,
                "nombre": ACTIVOS[t]["nombre"],
                "tipo": ACTIVOS[t]["tipo"],
                "velas": int(len(df)),
                "fecha_inicio": str(df["Date"].iloc[0].date()),
                "fecha_fin": str(df["Date"].iloc[-1].date()),
                "bh_retorno": round(float(bh), 2),
                "ann_factor": FACTORES_ANUALIZACION[ACTIVOS[t]["tipo"]],
            }
        )

    with open(f"{DIR_SALIDA}/resumen.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "ventana": {"inicio": VENTANA_INICIO, "fin": VENTANA_FIN},
                "modo": "Long/Short (+1/-1) sobre el retorno del día siguiente",
                "activos": resumen_activos,
                "experimentos": {
                    k: {
                        "memoria": v["memoria"],
                        "estados": v["estados"],
                        "estrategias": 2 ** v["estados"],
                    }
                    for k, v in EXPERIMENTOS.items()
                },
            },
            f, ensure_ascii=False, indent=2,
        )

    curvas_elite = None

    for exp_id, cfg in EXPERIMENTOS.items():
        n_estados = cfg["estados"]
        total = 2 ** n_estados
        print(f"\n[{exp_id}] Censo de {total:,} estrategias en {len(tickers)} activos...")

        # ---------------- PASO 1: torneo independiente por activo ----------------
        ret = {}     # ticker -> (total,) retorno %
        shp = {}
        dd = {}
        torneo_json = {}
        for t in tickers:
            ann = FACTORES_ANUALIZACION[ACTIVOS[t]["tipo"]]
            r, s, d = censo_activo(universo[t], cfg["columna"], n_estados, ann)
            ret[t], shp[t], dd[t] = r, s, d

            orden = np.argsort(-r)
            top_ids = orden[:TOP_TABLA]
            torneo_json[t] = {
                "resumen": {
                    "total": total,
                    "positivas": int((r > 0).sum()),
                    "pct_positivas": round(float((r > 0).mean()) * 100, 2),
                    "superan_bh": int((r > bh_por_activo[t]).sum()),
                    "bh_retorno": round(float(bh_por_activo[t]), 2),
                    "mediana_retorno": round(float(np.median(r)), 2),
                    "mejor": fila_metricas(orden[0], format(int(orden[0]), f"0{n_estados}b"),
                                           r[orden[0]], s[orden[0]], d[orden[0]]),
                },
                "top": [
                    fila_metricas(i, format(int(i), f"0{n_estados}b"), r[i], s[i], d[i])
                    for i in top_ids
                ],
            }
            print(f"  - {t:<9}: {int((r > 0).sum()):>6,} positivas | "
                  f"{int((r > bh_por_activo[t]).sum()):>6,} superan B&H "
                  f"({bh_por_activo[t]:.1f}%)")

        with open(f"{DIR_SALIDA}/torneo_{exp_id}.json", "w", encoding="utf-8") as f:
            json.dump(torneo_json, f, ensure_ascii=False)

        # ------------- PASO 2: pool anti-overfitting por activo -------------
        pools_json = {}
        for t in tickers:
            otros = [o for o in tickers if o != t]
            # Campeonas locales: superan Buy & Hold del activo con Sharpe > 0
            campeonas = (ret[t] > bh_por_activo[t]) & (shp[t] > 0)
            # Supervivientes: además, retorno positivo en TODOS los demás activos
            sobrevive = campeonas.copy()
            for o in otros:
                sobrevive &= ret[o] > 0

            ids = np.where(sobrevive)[0]
            # Orden por el peor retorno fuera de casa (robustez, no suerte local)
            if len(ids) > 0:
                min_cruce = np.min(np.stack([ret[o][ids] for o in otros]), axis=0)
                ids = ids[np.argsort(-min_cruce)]

            filas = []
            for i in ids[:TOP_POOL]:
                cruce = {o: round(float(ret[o][i]), 2) for o in otros}
                filas.append(
                    {
                        **fila_metricas(i, format(int(i), f"0{n_estados}b"),
                                        ret[t][i], shp[t][i], dd[t][i]),
                        "cruce": cruce,
                        "min_cruce": round(float(min(cruce.values())), 2),
                        "prom_cruce": round(float(np.mean(list(cruce.values()))), 2),
                    }
                )
            pools_json[t] = {
                "criterio": "Supera B&H local con Sharpe > 0 y retorno > 0 en todos los demás activos",
                "campeonas_locales": int(campeonas.sum()),
                "sobreviven": int(sobrevive.sum()),
                "pct_overfitting": round(
                    float(1 - sobrevive.sum() / campeonas.sum()) * 100, 2
                ) if campeonas.sum() > 0 else None,
                "pool": filas,
            }
            print(f"  [Pool {t}] campeonas locales: {int(campeonas.sum()):,} -> "
                  f"sobreviven fuera de casa: {int(sobrevive.sum()):,}")

        with open(f"{DIR_SALIDA}/pools_{exp_id}.json", "w", encoding="utf-8") as f:
            json.dump(pools_json, f, ensure_ascii=False)

        # ------------- PASO 3: élite universal y similitud -------------
        matriz_ret = np.stack([ret[t] for t in tickers])       # (activos, total)
        universal = np.all(matriz_ret > 0, axis=0)
        ids_uni = np.where(universal)[0]
        peor = matriz_ret.min(axis=0)
        if len(ids_uni) > 0:
            ids_uni = ids_uni[np.argsort(-peor[ids_uni])]

        # Casi universales: positivas en todos menos un activo (contexto)
        positivos = (matriz_ret > 0).sum(axis=0)
        ids_casi = np.where(positivos == len(tickers) - 1)[0]
        ids_casi = ids_casi[np.argsort(-peor[ids_casi])][:20] if len(ids_casi) else ids_casi

        consenso, familias = consenso_y_familias(
            ids_uni[: 4 * TOP_ELITE], n_estados, UMBRAL_HAMMING[exp_id]
        )

        def fila_universal(i):
            retornos = {t: round(float(ret[t][i]), 2) for t in tickers}
            return {
                "ID": int(i),
                "ADN": format(int(i), f"0{n_estados}b"),
                "retornos": retornos,
                "sharpes": {t: round(float(shp[t][i]), 2) for t in tickers},
                "suma": round(float(sum(retornos.values())), 2),
                "min": round(float(min(retornos.values())), 2),
            }

        elite_json = {
            "criterio": "Retorno > 0 en TODOS los activos simultáneamente, ordenado por el peor retorno (robustez)",
            "num_universales": int(universal.sum()),
            "num_casi_universales": int((positivos == len(tickers) - 1).sum()),
            "elite": [fila_universal(i) for i in ids_uni[:TOP_ELITE]],
            "casi_universales": [
                {
                    **fila_universal(i),
                    "falla": tickers[int(np.argmin(matriz_ret[:, i]))],
                }
                for i in ids_casi
            ],
            "consenso": consenso,
            "familias": familias[:15],
        }
        with open(f"{DIR_SALIDA}/elite_{exp_id}.json", "w", encoding="utf-8") as f:
            json.dump(elite_json, f, ensure_ascii=False)
        print(f"  [Élite {exp_id}] universales: {int(universal.sum()):,} de {total:,} "
              f"| familias detectadas: {len(familias)}")

        # Curvas de equity mensuales de la élite N4 para el dashboard
        if exp_id == "N4" and len(ids_uni) > 0:
            seleccion = ids_uni[:5]
            curvas_elite = {"labels": {}, "curvas": {}}
            for t in tickers:
                df = universo[t]
                meses = df["Date"].dt.strftime("%Y-%m")
                retornos_np = df["Next_Return"].to_numpy(dtype=np.float64)
                estados = df[cfg["columna"]].to_numpy()
                series = {"Buy_and_Hold": np.cumprod(1.0 + retornos_np)}
                for i in seleccion:
                    acciones = 2 * adn_de_ids(np.array([i]), n_estados)[0] - 1
                    series[f"Strat_{int(i)}"] = np.cumprod(
                        1.0 + acciones[estados] * retornos_np
                    )
                agrupado = {
                    k: [round(float(x), 4) for x in
                        pd.Series(v).groupby(meses.values).last()]
                    for k, v in series.items()
                }
                curvas_elite["labels"][t] = sorted(meses.unique().tolist())
                curvas_elite["curvas"][t] = agrupado

    if curvas_elite is not None:
        with open(f"{DIR_SALIDA}/equity_elite.json", "w", encoding="utf-8") as f:
            json.dump(curvas_elite, f, ensure_ascii=False)
        print("\n[+] Curvas de equity de la élite N4 exportadas.")

    print("\n" + "=" * 70)
    print("   SIMULACIÓN COMPLETA - RESULTADOS EN data/multi_activo/")
    print("=" * 70)


if __name__ == "__main__":
    main()
