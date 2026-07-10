"""
Experimento 14: El Portafolio Institucional (mezcla TSMOM + B&H).

El Exp. 13 estableció dos hechos: (a) el trend-following diversificado
tiene ventaja propia estadísticamente robusta (p=0.0005 tras costos), y
(b) el B&H diversificado rindió más en la década alcista. La pregunta
institucional no es "¿cuál de los dos?" sino "¿cuánto de cada uno?": si la
correlación entre ambos es baja, la mezcla debe superar en riesgo-ajuste a
sus dos componentes por el efecto de diversificación (el único almuerzo
gratis de las finanzas).

Se evalúan mezclas 0/25/50/75/100% TSMOM-252 (la primaria pre-registrada)
contra el B&H diversificado, ambas con la misma infraestructura del Exp.
13 (18 mercados, paridad de riesgo, costos, vol-targeting), re-balanceadas
diariamente a pesos constantes. Se reporta la correlación diaria entre
componentes y la inferencia estadística de cada mezcla.

Salida: data/multi_activo/institucional.json (pestaña 🏦 del dashboard).
"""
import json
import os
from datetime import datetime, timezone

import numpy as np

from src.meta_portfolio import inferencia, metricas
from src.meta_portfolio_v2 import (
    SAGRADA,
    cargar_mercados,
    construir,
    senales_siempre_largo,
)

DIR_SALIDA = "data/multi_activo"
MEZCLAS = [0.0, 0.25, 0.50, 0.75, 1.0]   # fracción en TSMOM-252


def main():
    print("=" * 70)
    print("   EXPERIMENTO 14: PORTAFOLIO INSTITUCIONAL (TSMOM + B&H)")
    print("=" * 70)

    b = cargar_mercados()
    print(f"\n[*] {len(b['mercados'])} mercados")

    tsmom = construir(b, b["senales"]["TSMOM-252 (primaria)"])
    bh = construir(b, senales_siempre_largo(b), con_costos=False)
    comunes = tsmom.index.intersection(bh.index)
    tsmom, bh = tsmom[comunes], bh[comunes]

    correlacion = float(np.corrcoef(tsmom.to_numpy(), bh.to_numpy())[0, 1])
    print(f"[*] Correlación diaria TSMOM-252 vs B&H diversificado: {correlacion:.3f}")

    resultados = []
    curvas = {}
    for w in MEZCLAS:
        mezcla = w * tsmom + (1 - w) * bh
        d = mezcla.to_numpy()
        etiqueta = f"{int(w * 100)}% TSMOM / {int((1 - w) * 100)}% B&H"
        resultados.append({
            "pct_tsmom": int(w * 100),
            "etiqueta": etiqueta,
            "total": metricas(d),
            "inferencia": inferencia(d),
            "sagrado": metricas(mezcla[mezcla.index >= SAGRADA].to_numpy()),
        })
        eq = (1 + mezcla).cumprod().resample("ME").last().dropna()
        curvas[etiqueta] = {
            "labels": [x.strftime("%Y-%m") for x in eq.index],
            "valores": [round(float(x), 4) for x in eq],
        }
        r = resultados[-1]
        print(f"  {etiqueta:<22}: ret {r['total']['retorno']:>8}% | sharpe {r['total']['sharpe']:>5} "
              f"| dd {r['total']['max_dd']:>7}% | t {r['inferencia']['t_stat']:>5}")

    mejor = max(resultados, key=lambda r: r["total"]["sharpe"])
    print(f"\n[MEJOR SHARPE] {mejor['etiqueta']}: {mejor['total']}")

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metodologia": "Mezclas de TSMOM-252 (con costos) y B&H diversificado, misma infraestructura del Exp. 13 (18 mercados, paridad de riesgo, vol-targeting 10%), rebalanceo diario a pesos constantes.",
        "correlacion_diaria": round(correlacion, 3),
        "sagrada_desde": SAGRADA,
        "mezclas": resultados,
        "mejor_sharpe": mejor["etiqueta"],
        "curvas": curvas,
    }
    os.makedirs(DIR_SALIDA, exist_ok=True)
    with open(f"{DIR_SALIDA}/institucional.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    print(f"[+] Resultados exportados a {DIR_SALIDA}/institucional.json")


if __name__ == "__main__":
    main()
