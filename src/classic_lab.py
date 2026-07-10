"""
Experimento 11: Las familias clásicas ante el Tribunal de 4 capas.

Las ~30 estrategias paramétricas de classic_strategies.py se juzgan con la
misma arquitectura del Experimento 10:

  - Ventana de selección (hasta 2025-07) con 4 cortes walk-forward.
  - Pista A (universales): retorno > 0 en los 11 mercados en train Y test
    de todos los cortes. Las que pasan rinden el examen sagrado.
  - Pista B (especialistas): superar al B&H de su mercado en train y test
    de todos los cortes con retorno > 0 en cada test; la mejor por mercado
    entra al portafolio (volatilidad inversa).
  - PERÍODO SAGRADO (2025-07 -> 2026-07): examen final intocado.

Ventaja estructural frente a los autómatas: ~30 hipótesis con prior
académico en vez de 65,536 sin él — el riesgo de que una superviviente sea
azar cae tres órdenes de magnitud.

Salida: data/multi_activo/clasicas.json (pestaña 🏛️ del dashboard).
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.classic_strategies import catalogo
from src.data_pipeline import ACTIVOS, cargar_universo, preparar_activo

DIR_SALIDA = "data/multi_activo"
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


def metricas(diarios, ann=252):
    equity = np.cumprod(1.0 + diarios)
    desv = diarios.std(ddof=1)
    return {
        "retorno": round(float((equity[-1] - 1) * 100), 2),
        "sharpe": round(float(np.sqrt(ann) * diarios.mean() / desv), 2) if desv > 0 else 0.0,
        "max_dd": round(float(((equity / np.maximum.accumulate(equity)) - 1).min() * 100), 2),
    }


def ret_total(diarios):
    return float((np.prod(1.0 + diarios) - 1.0) * 100)


def main():
    print("=" * 70)
    print("   EXPERIMENTO 11: FAMILIAS CLÁSICAS ANTE EL TRIBUNAL")
    print("=" * 70)

    universo = cargar_universo()
    nombres = {t: ACTIVOS[t]["nombre"] for t in universo}
    for tk, nombre in VIRGENES.items():
        df = preparar_activo(tk)
        if df is not None:
            universo[tk] = df
            nombres[tk] = nombre
    mercados = list(universo.keys())

    estrategias = catalogo()
    print(f"\n[*] {len(estrategias)} estrategias clásicas × {len(mercados)} mercados")

    # Retornos diarios de cada (estrategia, mercado) con sus fechas
    rendimientos = {}      # (nombre_estrategia, mercado) -> DataFrame[Date, r_estrategia, r_mercado]
    for t, df in universo.items():
        fechas = df["Date"]
        r_mercado = df["Next_Return"].to_numpy(dtype=np.float64)
        for nombre, fn in estrategias.items():
            pos = fn(df).to_numpy(dtype=np.float64)
            rendimientos[(nombre, t)] = pd.DataFrame(
                {"Date": fechas, "r": pos * r_mercado, "mercado": r_mercado}
            )

    def tramo(nombre, t, desde=None, hasta=None):
        d = rendimientos[(nombre, t)]
        if desde:
            d = d[d["Date"] >= desde]
        if hasta:
            d = d[d["Date"] < hasta]
        return d

    # ---------------- PISTA A: universales ----------------
    print("\n[PISTA A] Universales (positivas en los 11 mercados, todos los cortes)...")
    universales = []
    for nombre in estrategias:
        pasa = True
        for corte in CORTES_SEL:
            for t in mercados:
                tr = tramo(nombre, t, hasta=corte)
                te = tramo(nombre, t, desde=corte, hasta=SAGRADA)
                if len(tr) < MIN_TRAIN or len(te) < MIN_TEST:
                    continue
                if ret_total(tr["r"].to_numpy()) <= 0 or ret_total(te["r"].to_numpy()) <= 0:
                    pasa = False
                    break
            if not pasa:
                break
        if pasa:
            universales.append(nombre)
            print(f"  ✓ {nombre} sobrevive la selección universal")
    if not universales:
        print("  (ninguna estrategia clásica es universal en la selección)")

    candidatas_uni = []
    for nombre in universales:
        rets_sag = {t: round(ret_total(tramo(nombre, t, desde=SAGRADA)["r"].to_numpy()), 2)
                    for t in mercados}
        candidatas_uni.append({
            "nombre": nombre,
            "sagrada": rets_sag,
            "aprueba_sagrada": bool(all(v > 0 for v in rets_sag.values())),
        })
        print(f"  Sagrado de {nombre}: "
              f"{'APRUEBA' if candidatas_uni[-1]['aprueba_sagrada'] else 'FALLA'} | {rets_sag}")

    # ---------------- PISTA B: especialistas ----------------
    print("\n[PISTA B] Especialistas por mercado...")
    especialistas = {}
    componentes = []
    for t in mercados:
        supervivientes = []
        for nombre in estrategias:
            excesos = []
            ok = True
            for corte in CORTES_SEL:
                tr = tramo(nombre, t, hasta=corte)
                te = tramo(nombre, t, desde=corte, hasta=SAGRADA)
                if len(tr) < MIN_TRAIN or len(te) < MIN_TEST:
                    continue
                r_tr, bh_tr = ret_total(tr["r"].to_numpy()), ret_total(tr["mercado"].to_numpy())
                r_te, bh_te = ret_total(te["r"].to_numpy()), ret_total(te["mercado"].to_numpy())
                if not (r_tr > bh_tr and r_te > bh_te and r_te > 0):
                    ok = False
                    break
                excesos.append(r_te - bh_te)
            if ok and excesos:
                supervivientes.append((nombre, min(excesos)))

        elegido = None
        if supervivientes:
            nombre, peor_exceso = max(supervivientes, key=lambda x: x[1])
            sel = tramo(nombre, t, hasta=SAGRADA)["r"].to_numpy()
            sag = tramo(nombre, t, desde=SAGRADA)["r"].to_numpy()
            elegido = {
                "nombre": nombre,
                "peor_exceso_test": round(peor_exceso, 2),
                "vol_seleccion": float(sel.std(ddof=1)),
                "sagrada": metricas(sag),
            }
            componentes.append((t, nombre, elegido["vol_seleccion"]))
        especialistas[t] = {
            "nombre": nombres[t],
            "sobreviven": len(supervivientes),
            "candidatas": [n for n, _ in sorted(supervivientes, key=lambda x: -x[1])[:5]],
            "elegido": elegido,
        }
        print(f"  {nombres[t]:<24}: sobreviven {len(supervivientes):>2} | "
              f"{'elegida: ' + elegido['nombre'] if elegido else 'SIN especialista'}")

    # ---------------- Portafolio en el sagrado ----------------
    resumen_port = None
    if componentes:
        pesos_inv = np.array([1.0 / max(v, 1e-6) for _, _, v in componentes])
        pesos = pesos_inv / pesos_inv.sum()

        fechas = sorted(set().union(*[
            set(tramo(n, t, desde=SAGRADA)["Date"]) for t, n, _ in componentes]))
        idx = pd.DatetimeIndex(fechas)
        port = pd.Series(0.0, index=idx)
        bench = pd.Series(0.0, index=idx)
        for (t, n, _), w in zip(componentes, pesos):
            d = tramo(n, t, desde=SAGRADA)
            di = pd.DatetimeIndex(d["Date"])
            port += w * pd.Series(d["r"].to_numpy(), index=di).reindex(idx).fillna(0.0)
            bench += w * pd.Series(d["mercado"].to_numpy(), index=di).reindex(idx).fillna(0.0)
        d_spy = tramo(list(estrategias)[0], "SPY", desde=SAGRADA)
        spy = pd.Series(d_spy["mercado"].to_numpy(),
                        index=pd.DatetimeIndex(d_spy["Date"])).reindex(idx).fillna(0.0)

        semanal = {k: (1 + v).cumprod().resample("W-FRI").last().dropna()
                   for k, v in {"portafolio": port, "benchmark": bench, "spy": spy}.items()}
        resumen_port = {
            "componentes": [
                {"ticker": t, "nombre": nombres[t], "estrategia": n, "peso": round(float(w), 4)}
                for (t, n, _), w in zip(componentes, pesos)
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
        print("\n[SAGRADO] Portafolio clásico:", resumen_port["sagrada"]["portafolio"])
        print("[SAGRADO] Benchmark B&H (mismos pesos):", resumen_port["sagrada"]["benchmark_bh"])
        print("[SAGRADO] SPY:", resumen_port["sagrada"]["spy"])

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "num_estrategias": len(estrategias),
        "familias": "TSMOM, cruce de SMAs, Donchian, reversión RSI, filtro SMA largo plazo",
        "sagrada_desde": SAGRADA,
        "cortes_seleccion": CORTES_SEL,
        "criterio_universal": "Retorno > 0 en los 11 mercados en train Y test de todos los cortes",
        "criterio_especialista": "Superar al B&H de su mercado en train y test de todos los cortes, con retorno > 0 en cada test",
        "universales": {
            "supervivientes_seleccion": len(universales),
            "candidatas": candidatas_uni,
        },
        "especialistas": especialistas,
        "portafolio": resumen_port,
    }
    os.makedirs(DIR_SALIDA, exist_ok=True)
    with open(f"{DIR_SALIDA}/clasicas.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    print(f"\n[+] Resultados exportados a {DIR_SALIDA}/clasicas.json")


if __name__ == "__main__":
    main()
