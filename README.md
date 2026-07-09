# 🧬 Torneo Axelrod Crypto — Laboratorio Quant

Laboratorio de trading cuantitativo que aplica torneos evolutivos al estilo Axelrod
sobre mercados financieros, con un **tribunal de validación anti-overfitting de 4
capas**: multi-activo → walk-forward multi-corte → jurado virgen → período sagrado.

- 🧭 **[REFLEXIONES.md](REFLEXIONES.md)** — el informe final para colaboradores: el sistema 40/60 en detalle, la teoría que lo soporta, y las reflexiones sobre aleatoriedad, convexidad, overfitting, índices y cómo aprovecharlo en el mundo real.
- 📜 **[CONCLUSIONES.md](CONCLUSIONES.md)** — documento técnico de cierre: el hallazgo, su mecanismo económico y la cadena de inferencia (para expertos en finanzas/estadística).
- 📖 **[BITACORA.md](BITACORA.md)** — la historia científica completa y sus lecciones.
- 🗺️ **[ROADMAP.md](ROADMAP.md)** — detalle de cada experimento (5-15) y próximos pasos.
- 🤖 **[CLAUDE.md](CLAUDE.md)** — guía para colaboradores y asistentes (flujo de scripts, convenciones).

## Inicio rápido

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Windows
python -m src.multi_asset_tournament               # torneo multi-activo (Exp. 5)
python -m src.walk_forward                         # prueba temporal (Exp. 6)
python -m src.representation_lab                   # duelo de representaciones (Exp. 7)
python -m src.virgin_validation                    # jurado virgen (Exp. 8)
python -m src.specialist_test                      # prueba del especialista (Exp. 9)
python -m src.portfolio_survivors                  # portafolio + período sagrado (Exp. 10)
```

## Dashboard

Los resultados están versionados en `data/multi_activo/`, así que el dashboard
funciona sin re-ejecutar nada:

```bash
python -m http.server
# abrir http://localhost:8000
```

## Resultado principal

Dos hallazgos con el mismo estándar de evidencia:

1. **Negativo (Exps. 5-11):** tras ~1.5 millones de backtests, los autómatas fijos de
   estados diarios no contienen ventaja explotable que sobreviva a datos no vistos.
2. **Positivo (Exps. 12-15):** existe una **prima de tendencia** (TSMOM-252) débil pero
   estadísticamente robusta tras costos (t=3.10, p=0.0005), cuya mezcla 40/60 con
   Buy & Hold diversificado logra **Sharpe 1.09 con drawdown −18.9%** en 2015-2026 y
   **aprobó el período sagrado** (+14.7%, Sharpe 1.20 en 12 meses intocados).

Detalles, mecanismo económico y limitaciones en [CONCLUSIONES.md](CONCLUSIONES.md).
