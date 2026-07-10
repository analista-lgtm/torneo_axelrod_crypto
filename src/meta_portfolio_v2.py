"""
Experimento 13: Meta-Portafolio extendido (v2).

Extiende el Experimento 12 en las cuatro direcciones que refuerzan (o
refutan) la inferencia:

  1. HISTORIA: ventana 2015-07 -> 2026-07 (el doble de datos; cada mercado
     entra cuando su historia lo permite).
  2. DIVERSIFICACIÓN: ~18 mercados (se añaden cobre, maíz, gas natural,
     desarrollados ex-US, small caps, EUR/USD y DAX).
  3. COSTOS EXPLÍCITOS: 10 puntos básicos por unidad de rotación
     (cambio de señal) en cada mercado.
  4. VOL-TARGETING: apalancamiento causal del portafolio hacia 10% de
     volatilidad anual (vol rodante 63d del propio portafolio, rezagada
     un día, tope 2x).

La hipótesis primaria sigue siendo TSMOM-252 (pre-registrada en el Exp.
12); mismas secundarias con Bonferroni; misma inferencia (t-stat +
bootstrap por bloques). El "período sagrado" (2025-07 ->) se reporta.

Las funciones `cargar_mercados()` y `construir()` son reutilizadas por el
Experimento 14 (mezcla institucional TSMOM + B&H).

Salida: data/multi_activo/meta_portafolio_v2.json (mismo esquema que v1;
el dashboard la muestra con el selector de la pestaña 🌐).
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.classic_strategies import cruce_sma, donchian, tsmom
from src.data_pipeline import preparar_activo
from src.meta_portfolio import inferencia, metricas

DIR_SALIDA = "data/multi_activo"
INICIO = "2015-07-01"
FIN = "2026-07-01"
SAGRADA = "2025-07-01"
VOL_VENTANA = 63
COSTO = 0.001                 # 10 pb por unidad de rotación
VOL_OBJETIVO_ANUAL = 0.10
LEV_MAX = 2.0

MERCADOS = {
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SPY": "S&P 500 ETF",
    "GC=F": "Oro (Futuros)", "CL=F": "Petróleo WTI", "DX-Y.NYB": "Índice Dólar (DXY)",
    "TLT": "Bonos Tesoro 20+ años", "EEM": "Mercados Emergentes",
    "^N225": "Nikkei 225 (Japón)", "SI=F": "Plata (Futuros)", "USDJPY=X": "Dólar/Yen",
    "HG=F": "Cobre (Futuros)", "ZC=F": "Maíz (Futuros)", "NG=F": "Gas Natural (Futuros)",
    "EFA": "Desarrollados ex-US", "IWM": "Russell 2000 (Small Caps)",
    "EURUSD=X": "Euro/Dólar", "^GDAXI": "DAX 40 (Alemania)",
}

VARIANTES = {
    "TSMOM-252 (primaria)": lambda df: tsmom(df, 252),
    "TSMOM-126": lambda df: tsmom(df, 126),
    "SMA 50/200": lambda df: cruce_sma(df, 50, 200),
    "Donchian-100": lambda df: donchian(df, 100),
}


def cargar_mercados():
    """Descarga el universo y precalcula señales, retornos y pesos de riesgo."""
    universo = {}
    for tk in MERCADOS:
        df = preparar_activo(tk, inicio=INICIO, fin=FIN)
        if df is not None:
            universo[tk] = df
    mercados = list(universo.keys())

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
    return {
        "mercados": mercados, "senales": senales, "ret_mercado": ret_mercado,
        "peso_riesgo": peso_riesgo, "fechas_m": fechas_m, "calendario": calendario,
    }


def senales_siempre_largo(b):
    return {t: pd.Series(1.0, index=b["fechas_m"][t]) for t in b["mercados"]}


def construir_base(b, senal_por_mercado, con_costos=True):
    """Retornos diarios base: paridad de riesgo + costos, SIN vol-targeting."""
    calendario = b["calendario"]
    pesos_crudos, contrib = {}, {}
    for t in b["mercados"]:
        s = senal_por_mercado[t].reindex(calendario)
        w = b["peso_riesgo"][t].reindex(calendario)
        r = b["ret_mercado"][t].reindex(calendario)
        activo = s.notna() & w.notna() & np.isfinite(w) & r.notna()
        rotacion = s.fillna(0.0).diff().abs().fillna(0.0)
        bruto = s * r - (COSTO * rotacion if con_costos else 0.0)
        pesos_crudos[t] = w.where(activo, 0.0).fillna(0.0)
        contrib[t] = bruto.where(activo, 0.0).fillna(0.0)
    total_w = sum(pesos_crudos.values())
    base = pd.Series(0.0, index=calendario)
    for t in b["mercados"]:
        wn = (pesos_crudos[t] / total_w).where(total_w > 0, 0.0).fillna(0.0)
        base += wn * contrib[t]
    return base[total_w > 0]


def vol_target_rodante(base):
    """Vol-targeting clásico: vol rodante 63d del propio portafolio, rezagada 1 día."""
    vol_diaria_objetivo = VOL_OBJETIVO_ANUAL / np.sqrt(252)
    vol_port = base.rolling(VOL_VENTANA).std().shift(1)
    lev = (vol_diaria_objetivo / vol_port).clip(upper=LEV_MAX).fillna(1.0)
    return lev * base


def construir(b, senal_por_mercado, con_costos=True):
    """Retornos diarios: paridad de riesgo + costos por rotación + vol-target."""
    return vol_target_rodante(construir_base(b, senal_por_mercado, con_costos))


def main():
    print("=" * 70)
    print("   EXPERIMENTO 13: META-PORTAFOLIO v2 (2015-2026, COSTOS, VOL-TARGET)")
    print("=" * 70)

    b = cargar_mercados()
    mercados = b["mercados"]
    print(f"\n[*] {len(mercados)} mercados aceptados de {len(MERCADOS)} solicitados")

    bench = construir(b, senales_siempre_largo(b), con_costos=False)
    spy = b["ret_mercado"]["SPY"].reindex(b["calendario"]).dropna()

    resultados = {}
    for nombre_v in list(VARIANTES) + ["Ensamble (voto)"]:
        port = construir(b, b["senales"][nombre_v])
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
            "curva": {"labels": [x.strftime("%Y-%m") for x in eq_mensual.index],
                      "valores": [round(float(x), 4) for x in eq_mensual]},
        }
        r = resultados[nombre_v]
        print(f"\n  {nombre_v}")
        print(f"    total: {r['total']} | sagrado: {r['sagrado']['retorno']}%")
        print(f"    t-stat: {r['inferencia']['t_stat']} | p(boot): {r['inferencia']['p_bootstrap']} "
              f"| Sharpe CI95: {r['inferencia']['ci_sharpe_95']}")

    eq_bench = (1 + bench).cumprod().resample("ME").last().dropna()
    eq_spy = (1 + spy).cumprod().resample("ME").last().dropna()
    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metodologia": f"v2: ventana {INICIO}->{FIN}, {len(mercados)} mercados, costos de {COSTO*1e4:.0f} pb por rotación, vol-targeting {VOL_OBJETIVO_ANUAL:.0%} anual (63d causal, tope {LEV_MAX}x). Primaria pre-registrada: TSMOM-252. Bootstrap por bloques de 10 días.",
        "mercados": [{"ticker": t, "nombre": MERCADOS[t]} for t in mercados],
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
    with open(f"{DIR_SALIDA}/meta_portafolio_v2.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    print(f"\n[BENCHMARK B&H diversificado vol-target] {salida['benchmark_bh']['total']}")
    print(f"[+] Resultados exportados a {DIR_SALIDA}/meta_portafolio_v2.json")


if __name__ == "__main__":
    main()
