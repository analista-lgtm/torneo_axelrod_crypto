# CLAUDE.md

Guía para Claude Code (y colaboradores) al trabajar en este repositorio.

## Qué es este proyecto

**Torneo Axelrod Crypto Engine**: laboratorio de trading cuantitativo que aplica la Teoría de Juegos de Axelrod y autómatas celulares a mercados financieros. Codifica los últimos N días del mercado como estados binarios (subió = 1, bajó = 0) y genera *todas* las estrategias posibles (2^8 = 256 con N=3, 2^16 = 65,536 con N=4) para hacerlas competir en backtests masivos vectorizados. Ver `ROADMAP.md` para la historia completa de los experimentos y las fases futuras.

## Reglas de trabajo

- **Nunca trabajar directamente sobre `main`** — hay varias personas colaborando. Crear siempre una rama (`feature/...`) y trabajar ahí.
- Idioma del proyecto: **español** (comentarios, prints, documentación).
- Los resultados generados en `data/` están versionados a propósito: el dashboard `index.html` los consume directamente y los colaboradores los usan sin re-ejecutar simulaciones. Si un script regenera estos archivos, revisar el diff antes de commitear.

## Stack y entorno

- Python 3.12, dependencias en `requirements.txt` (pandas, numpy, requests, yfinance).
- Entorno virtual en `.venv/` (ignorado por git):
  ```powershell
  python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
  .venv\Scripts\python <script>
  ```
- No hay tests automatizados ni CI (por ahora).

## Estructura y flujo de ejecución

Los scripts forman una tubería — cada uno depende de la salida del anterior:

| Orden | Script | Qué hace | Genera |
|-------|--------|----------|--------|
| 1 | `main.py` | Descarga velas diarias de BTC desde Binance | `data/btc_1d_5y.csv` |
| 2 | `src/tournament.py` | Experimentos 2 y 3: torneo de 256 y 65,536 estrategias sobre BTC | `data/metrics_*.json`, `data/equity_*.json` |
| 3 | `src/cross_validation.py` | Experimento 4: valida campeonas de BTC en ETH, SPY, Oro, Petróleo, DXY | (solo consola) |
| 4 | `src/global_quantum_search.py` | Censo matricial de todas las estrategias en todos los activos | `data/censo_completo_*.json`, `data/elite_convergente_universal.json` |
| 5 | `src/multi_asset_tournament.py` | Experimento 5: torneos N=2/N=3/N=4 por activo en modos LS/LC + pools anti-overfitting + élite universal + comparativo de modos | `data/multi_activo/*.json` |
| 6 | `src/walk_forward.py` | Experimento 6: validación temporal train (21-24) / test (24-26) con lift vs. azar — **veredicto: overfitting temporal total en la representación actual** | `data/multi_activo/walkforward.json` |
| 7 | `src/representation_lab.py` | Experimento 7 (Fase 1.5): duelo de 4 representaciones (`src/representations.py`) bajo walk-forward de 4 cortes — la de **régimen** (SMA + volatilidad) es la única candidata (lift 3.87, 1 superviviente total) | `data/multi_activo/representaciones.json` |
| 8 | `src/virgin_validation.py` | Experimento 8: candidatas de régimen ante 5 activos vírgenes (TLT, EEM, Nikkei, plata, USDJPY) — **no aprueban el criterio estricto (lift 0)**; conclusión: ninguna estrategia individual de autómata fijo sobrevive todos los tests | `data/multi_activo/validacion_virgen.json` |
| 9 | `src/specialist_test.py` | Experimento 9: persistencia local por mercado sin exigencia cruzada (lift + Spearman train↔test) — la memoria explotable está en índices bursátiles (SPY 0.41, Nikkei 0.27) y **no en cripto** (BTC 0.11, ETH −0.11) | `data/multi_activo/especialistas.json` |
| 10 | `src/portfolio_survivors.py` | Experimento 10: doble pista (universales + especialistas por mercado) con **período sagrado** (últimos 12 meses intocados) — el portafolio de supervivientes **falla el examen sagrado** (−1.7% vs +18.5% B&H); cierre del arco: los autómatas fijos no contienen ventaja explotable | `data/multi_activo/portafolio.json` |
| 11 | `src/classic_lab.py` | Experimento 11: 28 estrategias clásicas (`src/classic_strategies.py`: TSMOM, SMAs, Donchian, RSI) ante el tribunal — 0 universales, 2 especialistas marginales, portafolio plano en el sagrado. Lección: las ventajas reales son débiles y requieren tests agregados, no supervivencia segmento a segmento | `data/multi_activo/clasicas.json` |
| 12 | `src/meta_portfolio.py` | Experimento 12 ⭐: TSMOM-252 pre-registrado, diversificado en 11 mercados con paridad de riesgo — **primera señal significativa** (Sharpe 0.67, t-stat 1.78, p=0.0355, DD un tercio menor que B&H); secundarias no pasan Bonferroni | `data/multi_activo/meta_portafolio.json` |
| 13 | `src/meta_portfolio_v2.py` | Experimento 13 ⭐⭐: v2 con 2015-2026, 18 mercados, costos 10 pb y vol-target 10% — TSMOM-252: t-stat 3.10, **p=0.0005, Sharpe CI95 [0.32, 1.26] excluye el cero**; TSMOM-126 y SMA 50/200 también pasan Bonferroni; el ensamble logra el menor DD (−15.5%) | `data/multi_activo/meta_portafolio_v2.json` |
| 14 | `src/institutional_blend.py` | Experimento 14: mezclas TSMOM+B&H (correlación 0.41) — **el óptimo es interior**: 25/75 da Sharpe 1.09 (vs 1.02 B&H puro) y 50/50 recorta el DD a −17.4%; conclusión práctica accionable | `data/multi_activo/institucional.json` |

La historia narrativa completa del laboratorio está en `BITACORA.md`; el resumen público en `README.md`.

`src/data_pipeline.py` es la capa estándar de ingesta (Yahoo Finance, misma ventana, misma limpieza y codificación para todos los activos) — cualquier análisis nuevo debe consumir datos a través de ella para mantener la comparabilidad.

**Convención canónica de identidad**: el ADN de una estrategia es la cadena binaria donde la posición `s` es la acción para el estado con código `s` ('1' = Long, '0' = Short); el ID es la lectura decimal del ADN (MSB = estado 0).

Ejecutar los scripts de `src/` **desde la raíz del repo** (usan rutas relativas como `data/...`): `python -m src.tournament` o `python src/cross_validation.py`.

Dashboard: `python -m http.server` y abrir `http://localhost:8000` (abre `index.html`; hace `fetch` de los JSON, no funciona como archivo local).

## Advertencias

- `src/tournament.py` y `src/global_quantum_search.py` simulan 65,536 estrategias: tardan varios minutos y consumen bastante RAM. No ejecutarlos como "smoke test" — para verificar cambios basta compilar/importar los módulos.
- `main.py` y los scripts 3-4 requieren internet (APIs de Binance y Yahoo Finance).
- Convención de datos: `Market_State` = 1 si el retorno diario > 0, si no 0; los códigos de estado (`Code_N2/N3/N4`) son la lectura decimal de la secuencia binaria de días, con el día más reciente como bit menos significativo.
