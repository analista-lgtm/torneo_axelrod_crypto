# Pre-registro: validación del pipeline de scoring de ForeBank CM (Fase 3 del plan de alineación)

*Escrito ANTES de correr cualquier backtest, conforme a la regla permanente #2 del plan
(`forebank-cm/docs/internal/PLAN-ALINEACION.md`) y al protocolo del tribunal de este
laboratorio. Fecha de congelación: 2026-07-14. Una sola corrida por variante; ninguna
variación de parámetros después de ver resultados.*

## Hipótesis

- **H1 (secundaria, informativa):** el pipeline de scoring de ForeBank (top-16 por score con
  gates, decisión mensual, pesos 1/vol, Long/Cash) supera a SPY buy & hold en Sharpe durante
  el período de evaluación 2015-07-01 → 2025-07-01.
- **H2 (primaria — decide la Fase 3):** el score complejo (7 categorías, ~40 tablas de
  interpolación, buckets, caps) supera a su **núcleo simple** (ranking 12-1 + gate 200d, mismo
  N, mismos pesos, misma cadencia, mismos costos) en Sharpe en el mismo período.

**Regla de decisión pre-comprometida:** si H2 falla (el score complejo NO supera al núcleo
simple), la Fase 3 concluye que la complejidad del modelo no paga y los pesos del modelo se
simplifican hacia el núcleo. Si H2 pasa, se documenta y se congela el score V2 con esta
evidencia. El período sagrado confirma o desmiente al final; no se optimiza nada contra él.

## Universo y datos

- **Universo:** constituyentes actuales del S&P 100 (lista congelada en
  `src/forebank_backtest.py`), GOOGL como única clase de Alphabet. Cada nombre entra al
  universo cuando acumula ≥260 sesiones de historia (point-in-time de listado).
- **Sesgo de supervivencia (reconocido):** la lista es la membresía actual, no la histórica.
  Esto infla por igual a las dos variantes activas (score complejo y núcleo simple), por lo
  que el veredicto operativo es la comparación relativa (H2). H1 vs SPY queda sesgada A FAVOR
  del stock-picking: si aun con ese viento a favor el score no supera a SPY, la evidencia en
  contra es fuerte; si lo supera, NO es prueba de alpha absoluto.
- **Proxies de sector:** ETFs SPDR de sector (XLK, XLC, XLY, XLP, XLV, XLF, XLI, XLE, XLU,
  XLRE, XLB) según el sector GICS de cada nombre; SPY como fallback cuando el ETF proxy aún
  no existía (XLC nace 2018-06, XLRE 2015-10). No se replica el nivel industry de
  `sector-taxonomy.js` (los ETFs de industria carecen de historia suficiente); se documenta
  como desviación conocida.
- **Datos:** Yahoo Finance vía `yfinance`, `auto_adjust=True` (total return), descarga desde
  2013-07-01 (buffer para ventanas de 252d).
- **Ventanas:** evaluación **2015-07-01 → 2025-07-01**; **período sagrado 2025-07-01 →
  2026-07-01** (se toca una sola vez, al final, con las reglas ya congeladas).

## Réplica del pipeline (fidelidad y desviaciones declaradas)

Fórmulas replicadas EXACTAMENTE de `netlify/functions/lib/scoring/` (commit `ed6666c`):

- `scoreFromRange` (interpolación lineal por tramos; sin dato → 60), `weightedAverage`
  (sin pesos válidos → 60), `bucketDown` (buckets 10…99), `countNotchDrop`.
- Categorías de precio: `assetMomentumScore`, `sectorMomentumScore` (con
  `sector_proxy_above_200d_score` binario 80/40 del ETF proxy), `trendDurabilityScore`,
  `riskScore` (beta y volatilidad vs SPY; `avg_dollar_volume` con volumen Yahoo;
  `market_cap` sin dato → 60 neutral).
- Métricas de mercado como `market-data-sync.js`: retornos 3m/6m/12-1 con skip-month
  (63/126/252/21 sesiones), SMA50/200, distancia al máximo 52s, RS 6m vs SPY, beta y vol
  1y sobre log-retornos, max drawdown 1y.
- Pesos del modelo: 35/20/10/15/10/5/5. **Fundamentales y manual overlay sin datos
  históricos** → cada componente cae al neutral que produce el propio motor con datos
  faltantes: quality = 60, valuation = 60, manual overlay = 72.5 (tiers standard/neutral/none,
  fórmula exacta). Esto reproduce el comportamiento real documentado del motor ante datos
  faltantes, y es la única forma honesta de backtestear sin fundamentales point-in-time.
- Caps y gates exactos de `engine.js`: precio<SMA200 → cap 65; MA50<MA200 → cap 70;
  drawdown ≤ −35% → cap 75; assetMomentum<60 → cap 65 y exit; sectorMomentum<65 → cap 70
  (sleeve momentum); elegibilidad = display ≥75 ∧ assetMomentum ≥70 ∧ sectorMomentum ≥65 ∧
  precio>SMA200. `actionState` exacto (incluye notch drops sobre el historial semanal).

## Reglas de cartera (mecánicas, congeladas)

Comunes a las dos variantes activas:

- Scoring semanal (último cierre de cada semana calendario). Decisión el primer día hábil
  de cada mes con el último scoring disponible.
- Cartera de **16 nombres máximo**; pesos ∝ 1/vol_252 renormalizados sobre lo invertido;
  los slots sin candidato elegible quedan en **cash (retorno 0)** — Long/Cash.
- Costos: **10 pb por lado** sobre el turnover (convención del laboratorio).

**Variante A — score complejo (el pipeline de ForeBank):**
- Entrada: `eligible == true`; ranking por `display_score` desc (desempate: raw score,
  ticker) — solo se compran nuevos nombres si hay slots libres.
- Salida: `actionState == 'exit'` al corte mensual (score<60 ∨ assetMomentum<60).
  `reduce`/`review`/`watch` mantienen sin comprar más.

**Variante B — núcleo simple (12-1 + gate 200d):**
- Señal: retorno 12-1 con skip-month. Entrada: 12-1 > 0 ∧ precio > SMA200, ranking por 12-1.
- Salida: precio < SMA200 al corte mensual.

**Benchmark:** SPY buy & hold (total return).

## Métricas y criterios de aprobación (congelados)

- Sharpe anualizado (252), CAGR, volatilidad, max drawdown, sobre el período de evaluación.
- H1: Sharpe_A > Sharpe_SPY. H2: Sharpe_A > Sharpe_B. t-stat del exceso mensual como
  evidencia de fuerza (no umbral de aprobación; con ~120 meses la potencia es limitada).
- **Multi-corte:** Sharpe por año calendario (10 cortes) — se reporta en cuántos años A
  supera a B y a SPY (consistencia, no criterio binario).
- **Sagrado:** tras congelar el veredicto de evaluación, una única pasada 2025-07 → 2026-07.

## Qué NO se hará

- Ni una sola variación de N, pesos, umbrales, ventanas o reglas tras ver resultados.
- No se elegirá "la mejor de varias corridas": hay exactamente una corrida por variante.
- El sagrado no se usa para decidir entre A y B; solo confirma o desmiente lo ya decidido.
