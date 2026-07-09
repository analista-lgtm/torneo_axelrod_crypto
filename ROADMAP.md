# 🗺️ Roadmap del Proyecto: Torneo Axelrod Crypto Engine

Este proyecto aplica los conceptos de la **Teoría de Juegos de Robert Axelrod (Estrategias Evolutivas)** y **Autómatas Celulares** al análisis cuantitativo de mercados financieros globales, utilizando una arquitectura de memoria de estados binarios ($2^N$).

---

## 🚀 Hitos Alcanzados (Milestones)

### 📈 Experimento 1: La Línea de Base (Baseline)
* **Objetivo:** Establecer el benchmark clásico del mercado utilizando una estrategia estática de *Buy & Hold* (Comprar y Mantener).
* **Resultado:** Sirve como el filtro mínimo de viabilidad. Cualquier estrategia que no supere el retorno absoluto de este experimento o que tenga un peor drawdown queda automáticamente descartada.

### 🧠 Experimento 2: Memoria de Corto Alcance ($2^3 = 8$ Estados)
* **Objetivo:** Analizar secuencias de mercado basadas en una memoria histórica de 3 días para un total de 256 estrategias posibles.
* **Resultado:** Se identificó una estructura básica de decisiones, pero el alcance predictivo resultó limitado frente a la volatilidad macro.

### 🧬 Experimento 3 & 3B: Universo Expandido ($2^4 = 16$ Estados)
* **Objetivo:** Expandir la matriz de memoria a 4 días secuenciales, generando un ecosistema de **65,536 estrategias** compitiendo simultáneamente en modo Long puro y Long/Short agresivo.
* **Resultados Destacados en Bitcoin (In-Sample: 2021 - 2026):**
  * `Strat_54245`: **+3,780.65%** de retorno absoluto.
  * `Strat_54247`: **+3,569.83%** de retorno absoluto.
  * **Filosofía Implícita Descubierta:** Las ganadoras operan como quimeras híbridas: compran pánico extremo (Mean Reversion), ejecutan cortos quirúrgicos en rebotes falsos (*Bull Traps*) y surfean rallies con FOMO institucional (Trend Following).

### 🧪 Experimento 4: Auditoría Anti-Overfitting Multi-Mercado
* **Objetivo:** Ejecutar las campeonas de Bitcoin fuera de su muestra (*Out-of-Sample*) en entornos macroeconómicos con densidades y correlaciones totalmente distintas (Ethereum, S&P 500, Oro, Petróleo, DXY).
* **Descubrimiento Crítico (Veredicto):** Se detectó un **sobreajuste (overfitting) masivo** en las estrategias líderes de rentabilidad absoluta. El rendimiento aislado en un único activo demostró ser el peor indicador de consistencia universal (ej. la líder de BTC destruyó el -79.26% de la cuenta en ETH debido a ligeras desalineaciones en las secuencias de velas diarias).

### 🛰️ Experimento 5: Torneo Multi-Activo Completo (Fase 1 — Completada)
* **Objetivo:** Abandonar el sesgo de selección: correr los 3 experimentos (N=2, N=3, N=4) de forma independiente sobre **cada** activo del universo (BTC, ETH, SPY, Oro, Petróleo, DXY) con una tubería de datos estandarizada, y auditar el overfitting en ambas direcciones.
* **Implementación:** `src/data_pipeline.py` (ingesta estándar) + `src/multi_asset_tournament.py` (censo vectorizado, pools anti-overfitting por activo y élite universal). Resultados en `data/multi_activo/` y visualización completa en el dashboard `index.html`.
* **Resultados Destacados (ventana 2021-07 → 2026-07):**
  * **Overfitting confirmado a escala:** de las ~10,000-24,000 campeonas locales de cada activo (N=4 Long/Short), sobreviven entre 1 y 32 fuera de casa (>99.8% de tasa de overfitting).
  * **14 estrategias universales** (N=4 Long/Short) con retorno positivo en los 6 mercados simultáneamente, agrupadas en 5 familias por distancia de Hamming.
  * **Duelo de modos (Long/Short vs Long/Cash):** el mismo ADN de la élite ejecutado en Long/Cash mejora el Sharpe promedio (10 de 10 casos) y el peor drawdown (10 de 10), a cambio de ceder algo de retorno máximo. La élite universal LC crece a 1,895 porque el modo no castiga los errores del bit 0 — el filtro cruzado es menos exigente y sus universales son menos informativos.
  * **ADN de consenso descubierto:** la élite converge en comprar pánico extremo (estado ▼▼▼▼ → 100% Long), vender el rebote falso (▼▼▼▲ → 100% Short) y surfear la tendencia (▲▲▲▲ → ~93% Long) — la filosofía "quimera" del Experimento 3 emerge de nuevo, pero ahora libre de sobreajuste.
  * En N=3 existe **una sola estrategia universal** (`10011111`), y su lógica es un sub-patrón exacto del consenso de N=4.

### ⏳ Experimento 6: Validación Walk-Forward (Overfitting Temporal) — Completada
* **Objetivo:** La robustez cruzada entre activos (Exp. 5) no garantiza robustez en el tiempo. Se seleccionó la élite universal usando **únicamente** el período train (2021-07 → 2024-06) y se evaluó en el período test (2024-07 → 2026-07), que la selección jamás vio. Métrica clave: el **lift** (tasa de supervivencia de la élite vs. tasa base del azar).
* **Implementación:** `src/walk_forward.py`, resultados en `data/multi_activo/walkforward.json` y pestaña "⏳ Walk-Forward" del dashboard. Motor verificado (siempre-Long replica el B&H de cada sub-período).
* **Veredicto (honesto y crítico): OVERFITTING TEMPORAL TOTAL.**
  * N=4 Long/Short: 371 universales del train → **0** sobreviven el test (tasa base del azar: 0.58%, esperados por suerte: ~2). Lift = 0.
  * N=4 Long/Cash: 8,627 universales del train → **2** sobreviven (0.02% vs. tasa base 0.86%). Lift = 0.03 — la élite del pasado rinde **peor que elegir estrategias al azar**.
  * La mediana del peor retorno en test de la élite train (−48.8%) es inferior a la del universo completo (−38.5%): los patrones ganadores de 2021-2024 tienden a *revertirse* en 2024-2026.
* **Implicación:** las 14 "universales" del Experimento 5 deben considerarse artefactos in-sample de la ventana completa hasta que se demuestre lo contrario. La representación actual (autómata binario de secuencias diarias exactas) captura regímenes, no leyes: es demasiado frágil ante el cambio de régimen. **No avanzar a algoritmos genéticos sobre esta representación** — evolucionarían ruido.

---

## 🔮 Próximos Pasos (Future Horizon)

### 🧪 Fase 1.5 (nueva, prerrequisito): Representación Robusta del Estado
* **Motivación:** El Experimento 6 demostró que los estados binarios de secuencias diarias exactas no persisten en el tiempo. Antes de evolucionar nada, hay que encontrar una codificación del mercado cuya élite pase el walk-forward con lift > 3.
* **Candidatos a explorar:** estados por magnitud y no solo signo (retornos grandes/pequeños), horizontes más largos (semanal), features de régimen (volatilidad, tendencia de medias móviles), y validación walk-forward con múltiples cortes (no uno solo).

### 🧬 Fase 2: Algorítmos Genéticos (Algorítmic Evolution)
* **Objetivo:** Implementar operadores de cruce (*crossover*), mutación de bits aleatoria y selección natural por torneo.
* **Meta:** Dejar que las estrategias evolucionen de forma autónoma generación tras generación, buscando la resiliencia en lugar del sobreajuste lineal.
* **Condición de entrada (aprendizaje del Exp. 6):** solo sobre una representación que ya haya demostrado persistencia temporal, con fitness walk-forward y un período de test final intocable.

### 🛡️ Fase 3: Gestión de Riesgo Dinámica (Money Management Layer)
* **Objetivo:** Sustituir la ejecución binaria agresiva de capital (100% Long / 100% Short) por un algoritmo de asignación proporcional de riesgo como el **Criterio de Kelly** o volatilidad inversa.
* **Meta:** Suavizar la curva de equidad (*Equity Curve*) y reducir los drawdowns máximos a menos del 15%.

---

## 🛠️ Requisitos e Instalación

Para clonar y continuar con el desarrollo del laboratorio quant, asegúrate de tener las dependencias al día:

```bash
pip install pandas numpy yfinance
python src/global_quantum_search.py