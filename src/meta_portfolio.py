"""
Experimento 12: El Meta-Portafolio Estadístico.

Lección del Exp. 11: las ventajas reales de mercado son débiles y pierden
segmentos individuales con frecuencia — no pueden aprobar criterios de
"ganar siempre". El instrumento correcto para una ventaja débil es la
agregación: aplicar LA MISMA regla, fijada a priori desde la literatura
(sin selección → sin sesgo de selección), sobre los 11 mercados a la vez
con paridad de riesgo, y preguntar si el promedio diversificado tiene
ventaja estadísticamente significativa.

Variantes (pre-registradas; la PRIMARIA es TSMOM-252, la definición
canónica de Moskowitz, Ooi & Pedersen 2012; las demás son secundarias y
se interpretan con corrección de Bonferroni):
  - TSMOM-252 (primaria), TSMOM-126, SMA 50/200, Donchian-100
  - Ensamble: voto mayoritario de las cuatro señales.

Construcción del portafolio (todo causal):
  - Señal por mercado en {-1, 0, +1} al cierre de t, aplicada a Next_Return.
  - Paridad de riesgo: peso ∝ 1/volatilidad rodante de 63 días del mercado,
    normalizado cada día entre los mercados con señal disponible.

Inferencia:
  - t-stat del retorno diario medio del portafolio (≈ Sharpe·√años).
  - Bootstrap por bloques de 10 días (2,000 remuestreos): p-valor de
    media ≤ 0 e intervalo de confianza del Sharpe anualizado.
  - Consistencia por año calendario y examen del período sagrado
    (2025-07 → 2026-07), que aquí es informativo (no hubo selección).

Salida: data/multi_activo/meta_portafolio.json (pestaña 🌐 del dashboard).
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.classic_strategies import cruce_sma, donchian, tsmom
from src.data_pipeline import ACTIVOS, cargar_universo, preparar_activo

DIR_SALIDA = "data/multi_activo"
SAGRADA = "2025-07-01"
VOL_VENTANA = 63
BLOQUE, N_BOOT, SEMILLA = 10, 2000, 42

VIRGENES = {
    "TLT": "Bonos Tesoro 20+ años",
    "EEM": "Mercados Emergentes",
    "^N225": "Nikkei 225 (Japón)",
    "SI=F": "Plata (Futuros)",
    "USDJPY=X": "Dólar/Yen",
}

VARIANTES = {
    "TSMOM-252 (primaria)": lambda df: tsmom(df, 252),
    "TSMOM-126": lambda df: tsmom(df, 126),
    "SMA 50/200": lambda df: cruce_sma(df, 50, 200),
    "Donchian-100": lambda df: donchian(df, 100),
}


def metricas(diarios, ann=252):
    diarios = np.asarray(diarios, dtype=np.float64)
    equity = np.cumprod(1.0 + diarios)
    desv = diarios.std(ddof=1)
    return {
        "retorno": round(float((equity[-1] - 1) * 100), 2),
        "sharpe": round(float(np.sqrt(ann) * diarios.mean() / desv), 2) if desv > 0 else 0.0,
        "max_dd": round(float(((equity / np.maximum.accumulate(equity)) - 1).min() * 100), 2),
    }


def inferencia(diarios, ann=252):
    """t-stat, p-valor normal y bootstrap por bloques del Sharpe."""
    d = np.asarray(diarios, dtype=np.float64)
    n = len(d)
    t = float(d.mean() / (d.std(ddof=1) / np.sqrt(n)))
    from math import erf, sqrt
    p_normal = 0.5 * (1 - erf(t / sqrt(2)))          # unilateral: media > 0

    rng = np.random.default_rng(SEMILLA)
    n_bloques = int(np.ceil(n / BLOQUE))
    inicios_max = n - BLOQUE
    sharpes, medias = [], []
    for _ in range(N_BOOT):
        inicios = rng.integers(0, inicios_max + 1, n_bloques)
        muestra = np.concatenate([d[i:i + BLOQUE] for i in inicios])[:n]
        s = muestra.std(ddof=1)
        medias.append(muestra.mean())
        sharpes.append(np.sqrt(ann) * muestra.mean() / s if s > 0 else 0.0)
    sharpes = np.array(sharpes)
    return {
        "t_stat": round(t, 2),
        "p_normal": round(p_normal, 4),
        "p_bootstrap": round(float((np.array(medias) <= 0).mean()), 4),
        "ci_sharpe_95": [round(float(np.percentile(sharpes, 2.5)), 2),
                         round(float(np.percentile(sharpes, 97.5)), 2)],
    }


def main():
    print("=" * 70)
    print("   EXPERIMENTO 12: META-PORTAFOLIO ESTADÍSTICO (TSMOM DIVERSIFICADO)")
    print("=" * 70)

    universo = cargar_universo()
    nombres = {t: ACTIVOS[t]["nombre"] for t in universo}
    for tk, nombre in VIRGENES.items():
        df = preparar_activo(tk)
        if df is not None:
            universo[tk] = df
            nombres[tk] = nombre
    mercados = list(universo.keys())
    print(f"\n[*] {len(mercados)} mercados | variantes: {list(VARIANTES)} + Ensamble")

    # Señales, retornos y pesos de riesgo por mercado (todo causal)
    senales = {v: {} for v in VARIANTES}
    senales["Ensamble (voto)"] = {}
    ret_mercado, peso_riesgo, fechas_m = {}, {}, {}
    for t, df in universo.items():
        fechas_m[t] = pd.DatetimeIndex(df["Date"])
        ret_mercado[t] = pd.Series(df["Next_Return"].to_numpy(dtype=np.float64), index=fechas_m[t])
        vol = df["Return"].rolling(VOL_VENTANA).std()
        peso_riesgo[t] = pd.Series((1.0 / vol).to_numpy(dtype=np.float64), index=fechas_m[t])
        votos = []
        for v, fn in VARIANTES.items():
            s = pd.Series(fn(df).to_numpy(dtype=np.float64), index=fechas_m[t])
            senales[v][t] = s
            votos.append(s)
        senales["Ensamble (voto)"][t] = np.sign(sum(votos))

    calendario = pd.DatetimeIndex(sorted(set().union(*[set(f) for f in fechas_m.values()])))

    def construir(senal_por_mercado):
        """Retornos diarios del portafolio con paridad de riesgo (causal)."""
        pesos_crudos, contrib = {}, {}
        for t in mercados:
            s = senal_por_mercado[t].reindex(calendario)
            w = peso_riesgo[t].reindex(calendario)
            r = ret_mercado[t].reindex(calendario)
            activo = s.notna() & w.notna() & np.isfinite(w) & r.notna()
            pesos_crudos[t] = (w.where(activo, 0.0)).fillna(0.0)
            contrib[t] = (s * r).where(activo, 0.0).fillna(0.0)
        total_w = sum(pesos_crudos.values())
        port = pd.Series(0.0, index=calendario)
        for t in mercados:
            wn = (pesos_crudos[t] / total_w).where(total_w > 0, 0.0).fillna(0.0)
            port += wn * contrib[t]
        return port[total_w > 0]

    # Benchmark: mismos pesos de riesgo, siempre largo (B&H diversificado)
    siempre_largo = {t: pd.Series(1.0, index=fechas_m[t]) for t in mercados}
    bench = construir(siempre_largo)
    spy = ret_mercado["SPY"].reindex(calendario).dropna()

    resultados = {}
    todas = dict(VARIANTES)
    todas["Ensamble (voto)"] = None
    for nombre_v in list(VARIANTES) + ["Ensamble (voto)"]:
        port = construir(senales[nombre_v])
        d = port.to_numpy()
        sag = port[port.index >= SAGRADA].to_numpy()
        por_anio = {str(a): round(float((np.prod(1 + g.to_numpy()) - 1) * 100), 2)
                    for a, g in port.groupby(port.index.year)}
        eq_mensual = (1 + port).cumprod().resample("ME").last().dropna()
        resultados[nombre_v] = {
            "total": metricas(d),
            "inferencia": inferencia(d),
            "por_anio": por_anio,
            "sagrado": metricas(sag),
            "curva": {
                "labels": [x.strftime("%Y-%m") for x in eq_mensual.index],
                "valores": [round(float(x), 4) for x in eq_mensual],
            },
        }
        r = resultados[nombre_v]
        print(f"\n  {nombre_v}")
        print(f"    total: {r['total']} | sagrado: {r['sagrado']['retorno']}%")
        print(f"    t-stat: {r['inferencia']['t_stat']} | p(boot): {r['inferencia']['p_bootstrap']} "
              f"| Sharpe CI95: {r['inferencia']['ci_sharpe_95']}")
        print(f"    por año: {por_anio}")

    eq_bench = (1 + bench).cumprod().resample("ME").last().dropna()
    eq_spy = (1 + spy).cumprod().resample("ME").last().dropna()
    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metodologia": "Reglas fijadas a priori (sin selección), aplicadas a los 11 mercados con paridad de riesgo (1/vol 63d). Primaria: TSMOM-252; secundarias con corrección de Bonferroni (α=0.05/4). Bootstrap por bloques de 10 días, 2,000 remuestreos.",
        "mercados": [{"ticker": t, "nombre": nombres[t]} for t in mercados],
        "sagrada_desde": SAGRADA,
        "variantes": resultados,
        "benchmark_bh": {
            "total": metricas(bench.to_numpy()),
            "sagrado": metricas(bench[bench.index >= SAGRADA].to_numpy()),
            "curva": {"labels": [x.strftime("%Y-%m") for x in eq_bench.index],
                      "valores": [round(float(x), 4) for x in eq_bench]},
        },
        "spy": {
            "total": metricas(spy.to_numpy()),
            "curva": {"labels": [x.strftime("%Y-%m") for x in eq_spy.index],
                      "valores": [round(float(x), 4) for x in eq_spy]},
        },
    }
    os.makedirs(DIR_SALIDA, exist_ok=True)
    with open(f"{DIR_SALIDA}/meta_portafolio.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    print(f"\n[BENCHMARK B&H diversificado] {salida['benchmark_bh']['total']}")
    print(f"[+] Resultados exportados a {DIR_SALIDA}/meta_portafolio.json")


if __name__ == "__main__":
    main()
