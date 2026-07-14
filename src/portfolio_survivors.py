"""
Experimento 10: El Portafolio de Supervivientes.

Síntesis de la campaña: en lugar de exigir una única estrategia que gane en
todo, se construye un portafolio de pares (mercado, estrategia) donde cada
componente demostró sobrevivir el tiempo EN SU PROPIO terreno, manteniendo
viva la búsqueda universal en paralelo.

Metodología anti-overfitting en tres capas:
  1. PERÍODO SAGRADO: los últimos 12 meses (2025-07 -> 2026-07) no se usan
     en NINGUNA selección. Son el examen final del portafolio completo,
     equivalente a haberlo operado en vivo.
  2. Pista A (universales): estrategias de régimen con retorno > 0 en los
     6 mercados originales en train Y test de TODOS los cortes de
     selección, y además positivas en los 5 vírgenes (ventana de
     selección). Las que pasan, rinden el examen sagrado multi-activo.
  3. Pista B (especialistas): por mercado y sin exigencia cruzada, la
     estrategia debe superar al Buy & Hold de SU mercado en train y test
     de TODOS los cortes, con retorno positivo en cada test. La mejor por
     mercado (por su peor exceso sobre B&H en los tests) entra al
     portafolio.

Portafolio: componentes ponderados por volatilidad inversa (estimada solo
con la ventana de selección) y evaluados en el período sagrado contra dos
referencias: los mismos pesos en Buy & Hold y el S&P 500.

Salida: data/multi_activo/portafolio.json (pestaña 💼 del dashboard).
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.data_pipeline import ACTIVOS, cargar_universo, preparar_activo
from src.multi_asset_tournament import adn_de_ids
from src.representation_lab import censo_retornos
from src.representations import rep_regimen

DIR_SALIDA = "data/multi_activo"
N_ESTADOS = 16
TOTAL = 2 ** N_ESTADOS
SAGRADA = "2025-07-01"
CORTES_SEL = ["2023-01-01", "2023-07-01", "2024-01-01", "2024-07-01"]
MIN_TRAIN, MIN_TEST, MIN_SAGRADA = 80, 60, 100

VIRGENES = {
    "TLT": "Bonos Tesoro 20+ años",
    "EEM": "Mercados Emergentes",
    "^N225": "Nikkei 225 (Japón)",
    "SI=F": "Plata (Futuros)",
    "USDJPY=X": "Dólar/Yen",
}


def retornos_diarios(serie, idx):
    """Serie de retornos diarios de la estrategia idx (Long/Short) sobre serie."""
    acciones = np.where(adn_de_ids(idx, N_ESTADOS)[0] == 1, 1, -1)
    return acciones[serie["Code"].to_numpy()] * serie["Next_Return"].to_numpy(dtype=np.float64)


def metricas(diarios, ann=252):
    equity = np.cumprod(1.0 + diarios)
    desv = diarios.std(ddof=1)
    return {
        "retorno": round(float((equity[-1] - 1) * 100), 2),
        "sharpe": round(float(np.sqrt(ann) * diarios.mean() / desv), 2) if desv > 0 else 0.0,
        "max_dd": round(float(((equity / np.maximum.accumulate(equity)) - 1).min() * 100), 2),
    }


def main():
    print("=" * 70)
    print("   EXPERIMENTO 10: PORTAFOLIO DE SUPERVIVIENTES (SAGRADO 2025-07)")
    print("=" * 70)

    universo = cargar_universo()
    nombres = {t: ACTIVOS[t]["nombre"] for t in universo}
    originales = list(universo.keys())
    for tk, nombre in VIRGENES.items():
        df = preparar_activo(tk)
        if df is not None:
            universo[tk] = df
            nombres[tk] = nombre

    series = {t: rep_regimen(df) for t, df in universo.items()}
    seleccion = {t: s[s["Date"] < SAGRADA] for t, s in series.items()}
    sagrada = {t: s[s["Date"] >= SAGRADA] for t, s in series.items()}
    for t in list(universo):
        if len(sagrada[t]) < MIN_SAGRADA:
            print(f"[-] {t} sin período sagrado suficiente. Excluido.")
            universo.pop(t), series.pop(t), seleccion.pop(t), sagrada.pop(t)

    # Censos por mercado y corte (ventana de selección únicamente)
    print("\n[*] Censos de selección (train/test por corte, test termina antes del sagrado)...")
    r_train, r_test = {}, {}
    for t, sel in seleccion.items():
        r_train[t], r_test[t] = {}, {}
        for corte in CORTES_SEL:
            tr, te = sel[sel["Date"] < corte], sel[sel["Date"] >= corte]
            if len(tr) < MIN_TRAIN or len(te) < MIN_TEST:
                continue
            r_train[t][corte] = censo_retornos(tr["Code"].to_numpy(),
                                               tr["Next_Return"].to_numpy(dtype=np.float64), N_ESTADOS)
            r_test[t][corte] = censo_retornos(te["Code"].to_numpy(),
                                              te["Next_Return"].to_numpy(dtype=np.float64), N_ESTADOS)

    # ---------------- PISTA A: universales ----------------
    print("\n[PISTA A] Búsqueda universal (6 originales, todos los cortes)...")
    uni = np.ones(TOTAL, dtype=bool)
    for corte in CORTES_SEL:
        m_tr = np.stack([r_train[t][corte] for t in originales])
        m_te = np.stack([r_test[t][corte] for t in originales])
        uni &= np.all(m_tr > 0, axis=0) & np.all(m_te > 0, axis=0)
    ids_uni = np.where(uni)[0]
    print(f"  Supervivientes de selección: {len(ids_uni)}")

    # Filtro virgen (dentro de la ventana de selección)
    aprobadas_virgen = []
    if len(ids_uni) > 0:
        r_virgen_sel = {tk: censo_retornos(seleccion[tk]["Code"].to_numpy(),
                                           seleccion[tk]["Next_Return"].to_numpy(dtype=np.float64),
                                           N_ESTADOS)
                        for tk in VIRGENES if tk in seleccion}
        for i in ids_uni:
            if all(r_virgen_sel[tk][i] > 0 for tk in r_virgen_sel):
                aprobadas_virgen.append(int(i))
    print(f"  Aprobadas también por los vírgenes: {len(aprobadas_virgen)}")

    candidatas_uni = []
    for i in aprobadas_virgen:
        rets_sag = {t: round(float((np.prod(1.0 + retornos_diarios(sagrada[t], i)) - 1) * 100), 2)
                    for t in originales}
        candidatas_uni.append({
            "ID": int(i),
            "ADN": format(int(i), f"0{N_ESTADOS}b"),
            "sagrada": rets_sag,
            "aprueba_sagrada": bool(all(v > 0 for v in rets_sag.values())),
        })
        print(f"  Universal {format(int(i), f'0{N_ESTADOS}b')} en el sagrado: {rets_sag} "
              f"-> {'APRUEBA' if candidatas_uni[-1]['aprueba_sagrada'] else 'FALLA'}")

    # ---------------- PISTA B: especialistas por mercado ----------------
    print("\n[PISTA B] Especialistas por mercado (sin exigencia cruzada)...")
    especialistas = {}
    componentes = []
    for t in series:
        cortes_ok = [c for c in CORTES_SEL if c in r_train[t]]
        if not cortes_ok:
            especialistas[t] = {"nombre": nombres[t], "sobreviven": 0, "elegido": None}
            continue
        sobrevive = np.ones(TOTAL, dtype=bool)
        excesos_test = []
        for c in cortes_ok:
            bh_tr, bh_te = r_train[t][c][TOTAL - 1], r_test[t][c][TOTAL - 1]
            sobrevive &= (r_train[t][c] > bh_tr) & (r_test[t][c] > bh_te) & (r_test[t][c] > 0)
            excesos_test.append(r_test[t][c] - bh_te)
        # descartar la B&H pura (siempre-Long no es una "estrategia")
        sobrevive[TOTAL - 1] = False
        ids = np.where(sobrevive)[0]
        elegido = None
        if len(ids) > 0:
            peor_exceso = np.min(np.stack(excesos_test), axis=0)
            mejor = ids[np.argmax(peor_exceso[ids])]
            diarios_sel = retornos_diarios(seleccion[t], int(mejor))
            elegido = {
                "ID": int(mejor),
                "ADN": format(int(mejor), f"0{N_ESTADOS}b"),
                "peor_exceso_test": round(float(peor_exceso[mejor]), 2),
                "vol_seleccion": float(diarios_sel.std(ddof=1)),
                "sagrada": metricas(retornos_diarios(sagrada[t], int(mejor))),
            }
            componentes.append((t, int(mejor), elegido["vol_seleccion"]))
        especialistas[t] = {"nombre": nombres[t], "sobreviven": int(len(ids)), "elegido": elegido}
        print(f"  {nombres[t]:<24}: sobreviven {len(ids):>5} | "
              f"{'elegido ' + elegido['ADN'] if elegido else 'SIN especialista'}")

    # ---------------- PORTAFOLIO en el período sagrado ----------------
    resumen_port = None
    if componentes:
        pesos_inv = np.array([1.0 / max(v, 1e-6) for _, _, v in componentes])
        pesos = pesos_inv / pesos_inv.sum()

        fechas = sorted(set().union(*[set(sagrada[t]["Date"]) for t, _, _ in componentes]))
        idx = pd.DatetimeIndex(fechas)
        port = pd.Series(0.0, index=idx)
        bench = pd.Series(0.0, index=idx)   # mismos pesos, Buy & Hold de cada mercado
        for (t, i, _), w in zip(componentes, pesos):
            s = sagrada[t]
            estrat = pd.Series(retornos_diarios(s, i), index=pd.DatetimeIndex(s["Date"])).reindex(idx).fillna(0.0)
            mercado = pd.Series(s["Next_Return"].to_numpy(dtype=np.float64),
                                index=pd.DatetimeIndex(s["Date"])).reindex(idx).fillna(0.0)
            port += w * estrat
            bench += w * mercado

        spy = pd.Series(sagrada["SPY"]["Next_Return"].to_numpy(dtype=np.float64),
                        index=pd.DatetimeIndex(sagrada["SPY"]["Date"])).reindex(idx).fillna(0.0)

        eq = {"portafolio": (1 + port).cumprod(), "benchmark": (1 + bench).cumprod(),
              "spy": (1 + spy).cumprod()}
        semanal = {k: v.resample("W-FRI").last().dropna() for k, v in eq.items()}
        resumen_port = {
            "componentes": [
                {"ticker": t, "nombre": nombres[t], "ADN": format(i, f"0{N_ESTADOS}b"),
                 "peso": round(float(w), 4)}
                for (t, i, _), w in zip(componentes, pesos)
            ],
            "sagrada": {
                "portafolio": metricas(port.to_numpy()),
                "benchmark_bh": metricas(bench.to_numpy()),
                "spy": metricas(spy.to_numpy()),
            },
            "curva": {
                "labels": [d.strftime("%Y-%m-%d") for d in semanal["portafolio"].index],
                "portafolio": [round(float(x), 4) for x in semanal["portafolio"]],
                "benchmark": [round(float(x), 4) for x in semanal["benchmark"]],
                "spy": [round(float(x), 4) for x in semanal["spy"]],
            },
        }
        print("\n[SAGRADO] Portafolio:", resumen_port["sagrada"]["portafolio"])
        print("[SAGRADO] Benchmark B&H (mismos pesos):", resumen_port["sagrada"]["benchmark_bh"])
        print("[SAGRADO] SPY:", resumen_port["sagrada"]["spy"])

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "representacion": "regimen",
        "sagrada_desde": SAGRADA,
        "cortes_seleccion": CORTES_SEL,
        "criterio_universal": "Retorno > 0 en los 6 originales en train Y test de todos los cortes + positiva en los 5 vírgenes (ventana de selección)",
        "criterio_especialista": "Superar al B&H de su mercado en train y test de TODOS los cortes, con retorno > 0 en cada test (B&H pura excluida)",
        "universales": {
            "supervivientes_seleccion": int(len(ids_uni)),
            "aprobadas_virgen": len(aprobadas_virgen),
            "candidatas": candidatas_uni,
        },
        "especialistas": especialistas,
        "portafolio": resumen_port,
    }
    os.makedirs(DIR_SALIDA, exist_ok=True)
    with open(f"{DIR_SALIDA}/portafolio.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    print(f"\n[+] Resultados exportados a {DIR_SALIDA}/portafolio.json")


if __name__ == "__main__":
    main()
