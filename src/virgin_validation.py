"""
Experimento 8: Validación en Activos Vírgenes (el out-of-sample definitivo).

La representación de régimen produjo 1 superviviente total (4/4 cortes
walk-forward) y una familia de casi-supervivientes. Pero esos activos ya
participaron en la selección. La prueba final: evaluar a las candidatas en
mercados que NINGÚN experimento ha tocado jamás.

Jurado virgen: bonos del Tesoro (TLT), mercados emergentes (EEM),
Nikkei 225, plata (SI=F) y dólar/yen (USDJPY=X). Nota honesta: ningún
activo es 100% independiente (la plata correlaciona con el oro, el yen con
el DXY), pero sus motores macro — tasas, Asia, metales industriales — no
participaron en ninguna selección previa.

Candidatas: estrategias de régimen que sobrevivieron >= 3 de los 4 cortes
del Experimento 7 (la ID 52982 es la única con 4/4).

Métrica: lift = tasa de éxito de las candidatas en el jurado virgen
(retorno > 0 en TODOS los vírgenes) vs. la tasa base de las 65,536.

Salida: data/multi_activo/validacion_virgen.json (pestaña 🌱 del dashboard).
"""
import json
import os
from datetime import datetime, timezone

import numpy as np

from src.data_pipeline import FACTORES_ANUALIZACION, preparar_activo, cargar_universo
from src.multi_asset_tournament import adn_de_ids
from src.representation_lab import CORTES, censo_retornos
from src.representations import rep_regimen

DIR_SALIDA = "data/multi_activo"
N_ESTADOS = 16
TOTAL = 2 ** N_ESTADOS
MIN_PASES = 3            # cortes walk-forward superados para ser candidata

VIRGENES = {
    "TLT": {"nombre": "Bonos Tesoro 20+ años", "tipo": "tradicional"},
    "EEM": {"nombre": "Mercados Emergentes", "tipo": "tradicional"},
    "^N225": {"nombre": "Nikkei 225 (Japón)", "tipo": "tradicional"},
    "SI=F": {"nombre": "Plata (Futuros)", "tipo": "tradicional"},
    "USDJPY=X": {"nombre": "Dólar/Yen", "tipo": "tradicional"},
}


def metricas_estrategia(serie, idx, ann_factor):
    """Retorno, Sharpe y MaxDD de una estrategia concreta (modo Long/Short)."""
    estados = serie["Code"].to_numpy()
    rets = serie["Next_Return"].to_numpy(dtype=np.float64)
    acciones = np.where(adn_de_ids(idx, N_ESTADOS)[0] == 1, 1, -1)
    diarios = acciones[estados] * rets
    equity = np.cumprod(1.0 + diarios)
    desv = diarios.std(ddof=1)
    return {
        "ret": round(float((equity[-1] - 1) * 100), 2),
        "sharpe": round(float(np.sqrt(ann_factor) * diarios.mean() / desv), 2) if desv > 0 else 0.0,
        "dd": round(float(((equity / np.maximum.accumulate(equity)) - 1).min() * 100), 2),
    }


def main():
    print("=" * 70)
    print("   EXPERIMENTO 8: VALIDACIÓN EN ACTIVOS VÍRGENES (RÉGIMEN)")
    print("=" * 70)

    # ---- 1. Reconstruir las candidatas desde el universo original ----
    print("\n[*] Reconstruyendo candidatas (supervivientes de >= "
          f"{MIN_PASES} de {len(CORTES)} cortes walk-forward)...")
    universo = cargar_universo()
    tickers_orig = list(universo.keys())
    series_orig = {t: rep_regimen(universo[t]) for t in tickers_orig}

    pases = np.zeros(TOTAL, dtype=int)
    for corte in CORTES:
        m_train, m_test = [], []
        for t in tickers_orig:
            d = series_orig[t]
            tr, te = d[d["Date"] < corte], d[d["Date"] >= corte]
            m_train.append(censo_retornos(tr["Code"].to_numpy(),
                                          tr["Next_Return"].to_numpy(dtype=np.float64), N_ESTADOS))
            m_test.append(censo_retornos(te["Code"].to_numpy(),
                                         te["Next_Return"].to_numpy(dtype=np.float64), N_ESTADOS))
        sobrevive = np.all(np.stack(m_train) > 0, axis=0) & np.all(np.stack(m_test) > 0, axis=0)
        pases += sobrevive.astype(int)

    candidatas = np.where(pases >= MIN_PASES)[0]
    print(f"[OK] Candidatas: {len(candidatas)} "
          f"(con 4/4 cortes: {int((pases == 4).sum())}, con 3/4: {int((pases == 3).sum())})")

    # ---- 2. Preparar el jurado virgen con la misma tubería estándar ----
    series_virgen = {}
    meta_virgen = []
    for tk, info in VIRGENES.items():
        df = preparar_activo(tk)
        if df is None:
            print(f"[-] {tk} descartado del jurado.")
            continue
        serie = rep_regimen(df)
        series_virgen[tk] = serie
        bh = (np.prod(1.0 + serie["Next_Return"].to_numpy()) - 1.0) * 100
        meta_virgen.append({
            "ticker": tk, "nombre": info["nombre"], "velas": int(len(serie)),
            "bh_retorno": round(float(bh), 2),
        })
        print(f"[OK] {tk}: {len(serie)} velas de régimen | B&H {bh:.1f}%")
    if len(series_virgen) < 4:
        print("[-] Jurado virgen insuficiente. Abortando.")
        return
    tickers_v = list(series_virgen.keys())

    # ---- 3. Censo completo en los vírgenes: tasa base vs candidatas ----
    ret_v = {tk: censo_retornos(series_virgen[tk]["Code"].to_numpy(),
                                series_virgen[tk]["Next_Return"].to_numpy(dtype=np.float64),
                                N_ESTADOS)
             for tk in tickers_v}
    matriz_v = np.stack([ret_v[tk] for tk in tickers_v])
    uni_virgen = np.all(matriz_v > 0, axis=0)
    min_v = matriz_v.min(axis=0)

    base_rate = float(uni_virgen.mean())
    aprobadas = candidatas[uni_virgen[candidatas]]
    tasa_cand = float(uni_virgen[candidatas].mean()) if len(candidatas) else None
    lift = round(tasa_cand / base_rate, 2) if (tasa_cand is not None and base_rate > 0) else None

    print(f"\n[JURADO] Tasa base (todas las estrategias positivas en {len(tickers_v)} vírgenes): "
          f"{base_rate * 100:.2f}%")
    print(f"[JURADO] Candidatas que aprueban: {len(aprobadas)} de {len(candidatas)} "
          f"({(tasa_cand or 0) * 100:.1f}%) | LIFT: {lift}")

    # ---- 4. Detalle por candidata (ordenadas: pases, luego peor virgen) ----
    orden = candidatas[np.lexsort((-min_v[candidatas], -pases[candidatas]))]
    filas = []
    for i in orden:
        filas.append({
            "ID": int(i),
            "ADN": format(int(i), f"0{N_ESTADOS}b"),
            "pases_walkforward": int(pases[i]),
            "retornos": {tk: round(float(ret_v[tk][i]), 2) for tk in tickers_v},
            "min": round(float(min_v[i]), 2),
            "aprueba": bool(uni_virgen[i]),
        })

    # Métricas completas de las aprobadas (y siempre de la 52982)
    detalle_aprobadas = {}
    destacadas = list(aprobadas) + ([52982] if 52982 not in aprobadas else [])
    for i in destacadas:
        detalle_aprobadas[str(int(i))] = {
            tk: metricas_estrategia(series_virgen[tk], int(i),
                                    FACTORES_ANUALIZACION[VIRGENES[tk]["tipo"]])
            for tk in tickers_v
        }

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "representacion": "regimen",
        "criterio_candidatas": f"Sobrevivir >= {MIN_PASES} de {len(CORTES)} cortes walk-forward (Exp. 7)",
        "criterio_aprobacion": "Retorno > 0 en TODOS los activos vírgenes (ventana completa)",
        "jurado": meta_virgen,
        "num_candidatas": int(len(candidatas)),
        "base_rate_pct": round(base_rate * 100, 2),
        "aprueban": int(len(aprobadas)),
        "tasa_candidatas_pct": round((tasa_cand or 0) * 100, 2),
        "lift": lift,
        "candidatas": filas,
        "metricas_aprobadas": detalle_aprobadas,
    }
    os.makedirs(DIR_SALIDA, exist_ok=True)
    with open(f"{DIR_SALIDA}/validacion_virgen.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    print(f"\n[+] Resultados exportados a {DIR_SALIDA}/validacion_virgen.json")


if __name__ == "__main__":
    main()
