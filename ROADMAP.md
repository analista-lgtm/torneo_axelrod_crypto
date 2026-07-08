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

---

## 🔮 Próximos Pasos (Future Horizon)

### 🛰️ Fase 1: El Buscador Matricial Global (En Desarrollo Actual)
* **Objetivo:** Abandonar el sesgo de selección. En lugar de validar solo las ganadoras de Bitcoin, ejecutar un algoritmo vectorizado en NumPy para auditar las 65,536 estrategias contra todos los mercados de forma simultánea.
* **Meta:** Filtrar y aislar las "Ciudadanas del Mundo": estrategias que quizás no ganen 3,000% en un activo, pero que mantengan un Sharpe Ratio positivo y retornos consistentes en **todos** los mercados a la vez.

### 🧬 Fase 2: Algorítmos Genéticos (Algorítmic Evolution)
* **Objetivo:** Implementar operadores de cruce (*crossover*), mutación de bits aleatoria y selección natural por torneo.
* **Meta:** Dejar que las estrategias evolucionen de forma autónoma generación tras generación, buscando la resiliencia en lugar del sobreajuste lineal.

### 🛡️ Fase 3: Gestión de Riesgo Dinámica (Money Management Layer)
* **Objetivo:** Sustituir la ejecución binaria agresiva de capital (100% Long / 100% Short) por un algoritmo de asignación proporcional de riesgo como el **Criterio de Kelly** o volatilidad inversa.
* **Meta:** Suavizar la curva de equidad (*Equity Curve*) y reducir los drawdowns máximos a menos del 15%.

---

## 🛠️ Requisitos e Instalación

Para clonar y continuar con el desarrollo del laboratorio quant, asegúrate de tener las dependencias al día:

```bash
pip install pandas numpy yfinance
python src/global_quantum_search.py