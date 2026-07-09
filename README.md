# 🧬 Torneo Axelrod Crypto — Laboratorio Quant

Laboratorio de trading cuantitativo que aplica torneos evolutivos al estilo Axelrod
sobre mercados financieros, con un **tribunal de validación anti-overfitting de 4
capas**: multi-activo → walk-forward multi-corte → jurado virgen → período sagrado.

- 📖 **[BITACORA.md](BITACORA.md)** — la historia científica completa (Exps. 5-10) y sus lecciones.
- 🗺️ **[ROADMAP.md](ROADMAP.md)** — detalle de cada experimento y próximos pasos.
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

## Resultado principal (hasta ahora)

Tras ~1.5 millones de backtests, los autómatas fijos de estados diarios **no
contienen ventaja explotable** que sobreviva a un período genuinamente no visto.
El activo del proyecto es el tribunal de validación, listo para juzgar cualquier
familia nueva de estrategias. Detalles y matices en la [bitácora](BITACORA.md).
