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

### 🌱 Experimento 8: Validación en Activos Vírgenes — Completada
* **Objetivo:** El out-of-sample definitivo. Las candidatas de régimen (supervivientes de ≥3 de 4 cortes del Exp. 7: la ID 52982 con 4/4 y dos vecinas con 3/4) se evaluaron en 5 mercados que ningún experimento tocó jamás: bonos del Tesoro (TLT), emergentes (EEM), Nikkei 225, plata (SI=F) y dólar/yen (USDJPY=X).
* **Implementación:** `src/virgin_validation.py`, resultados en `data/multi_activo/validacion_virgen.json` y pestaña "🌱 Activos Vírgenes" del dashboard.
* **Veredicto: NO APRUEBA el criterio estricto.** 0 de 3 candidatas logran retorno positivo en los 5 vírgenes (tasa base del azar: 3.42%, lift 0).
* **Matiz relevante (honesto en ambas direcciones):** la ID 52982 no colapsó como las élites del Exp. 6 — ganó con fuerza en 3 de 5 vírgenes (EEM +154%, Plata +87%, USDJPY +55%) y perdió poco en los otros dos (TLT −7.4%, Nikkei −6.1%). El perfil es cualitativamente mejor que el de cualquier estrategia anterior, pero "mejor que las anteriores" no es el estándar: el estándar es superar al azar con claridad, y no lo hizo.
* **Conclusión de la campaña (Exps. 5-8):** tras censar 65,536 estrategias × 4 representaciones × 2 modos × 11 activos × walk-forward multi-corte, **ninguna estrategia individual de autómata fijo sobrevive todos los tests**. Esto es un resultado científico, no un fracaso: el espacio de autómatas binarios sobre estados diarios no contiene ventajas persistentes y explotables a esta granularidad. El activo real del proyecto es el **tribunal de validación** (multi-activo + multi-corte + jurado virgen), reutilizable para cualquier hipótesis futura en minutos.

### 🎯 Experimento 9: La Prueba del Especialista — Completada
* **Hipótesis a probar:** los mercados son distintos por naturaleza y una estrategia puede ser rentable solo en el suyo (una especialista de BTC no necesita funcionar en divisas). Lo que la hipótesis no elimina: la especialista debe funcionar en el futuro de *su propio* mercado.
* **Implementación:** `src/specialist_test.py` — para cada uno de los 11 mercados, sin exigencia cruzada: campeonas del train (retorno > B&H local) evaluadas contra el B&H de su mercado en test (4 cortes × 2 representaciones). Métricas: lift local y correlación de Spearman del ranking completo de las 65,536 estrategias entre train y test. Pestaña "🎯 Especialistas" del dashboard.
* **Resultados (lift promedio | Spearman promedio):**
  * ✳️ Con persistencia débil pero real: **S&P 500 (2.56× | 0.41)**, **Nikkei 225 (2.84× | 0.27)**, Petróleo (1.27× | 0.36), Bonos TLT (1.12× | 0.35), USDJPY (1.69× | 0.25).
  * ❌ Sin persistencia: **Bitcoin (1.13× | 0.11)**, **Ethereum (0.88× | −0.11)**, DXY (0.94× | −0.06), Plata (0.52× | 0.11).
  * Global: lift 1.46×, Spearman 0.17 — memoria débil, existente, heterogénea.
* **Conclusión (el giro irónico):** la hipótesis de especialización es correcta en dirección pero invertida en objetivo: **los mercados con más memoria explotable son los índices bursátiles y las tasas, y los que menos tienen son las criptomonedas** — justo donde nació el proyecto. Ningún mercado alcanza el estándar duro (lift ≥ 3), pero SPY y Nikkei quedan cerca, lo que apunta a que la señal aprovechable es la de tendencia/momentum en índices, no los patrones diarios en cripto.

### 💼 Experimento 10: El Portafolio de Supervivientes — Completado
* **Objetivo (doble pista):** mantener viva la búsqueda universal Y construir un portafolio de especialistas por mercado que venzan el overfitting temporal cada uno en su terreno. Novedad metodológica: **período sagrado** — los últimos 12 meses (2025-07 → 2026-07) no participan en ninguna selección; son el examen final, equivalente a operar en vivo.
* **Implementación:** `src/portfolio_survivors.py`, resultados en `data/multi_activo/portafolio.json` y pestaña "💼 Portafolio" del dashboard. Selección con 4 cortes walk-forward dentro de la ventana de selección; portafolio ponderado por volatilidad inversa.
* **Pista A (universales): 0 supervivientes** — con los tests truncados antes del sagrado, ninguna estrategia de régimen es universal en train y test de todos los cortes.
* **Pista B (especialistas):** 10 de 11 mercados produjeron especialistas que superan a su B&H en todos los cortes de selección (desde 19 en plata hasta 13,643 en petróleo — abundan justo donde el B&H fue plano o negativo, señal de sesgo corto más que de habilidad).
* **Veredicto del examen sagrado: ❌ EL PORTAFOLIO FALLA.** Retorno −1.71% (Sharpe −0.15) contra +18.51% (Sharpe 1.73) de los mismos pesos en Buy & Hold y +22.24% del S&P 500. Los especialistas seleccionados con todo el rigor walk-forward no sobrevivieron el año que nadie vio.
* **Cierre del arco científico (Exps. 5-10):** la familia completa de autómatas fijos de 16 estados — universales, especialistas o en portafolio, en cualquier representación probada — **no contiene ventaja explotable que sobreviva a un período genuinamente no visto**. La persistencia débil detectada en índices (Exp. 9, Spearman ≤ 0.41) es real pero insuficiente para seleccionar estrategias individuales ganadoras. Este es el resultado del proyecto: un no-resultado robusto, demostrado con el estándar más alto, y un **tribunal de validación de 4 capas** (multi-activo → walk-forward multi-corte → jurado virgen → período sagrado) listo para cualquier hipótesis futura.

---

## 🔮 Próximos Pasos (Future Horizon)

### 🧪 Fase 1.5: Laboratorio de Representaciones — Completada (Experimento 7)
* **Motivación:** El Experimento 6 demostró que los estados binarios de secuencias diarias exactas no persisten en el tiempo. Antes de evolucionar nada, hay que encontrar una codificación del mercado cuya élite pase el walk-forward con lift > 3.
* **Implementación:** `src/representations.py` (codificaciones causales, sin fuga de futuro) + `src/representation_lab.py` (walk-forward con 4 cortes temporales distintos, modo Long/Short). Resultados en `data/multi_activo/representaciones.json` y pestaña "🔬 Representaciones" del dashboard.
* **Resultados del duelo de representaciones (lift promedio en 4 cortes | supervivientes en TODOS los cortes):**
  | Representación | Lift promedio | Supervivientes totales | Veredicto |
  |---|---|---|---|
  | Secuencia diaria N=4 (línea base) | 0.0 | 0 | ❌ Confirmado el Exp. 6 |
  | Signo + magnitud (2 días) | 0.1 | 0 | ❌ Descartada |
  | Secuencia semanal N=3 | 0.0 | 0 | ❌ Descartada |
  | **Régimen (SMA20/SMA50 + volatilidad + día)** | **3.87** | **1** | 🟡 **Candidata** |
* **La superviviente (`ID 52982`, ADN `1100111011110110`):** positiva en los 6 activos en la ventana completa (peor caso: +21.7% en DXY; ETH +548%) y universal en train Y test en los 4 cortes. Su lógica es interpretable: corto en tendencia bajista con volatilidad alta, largo en retrocesos dentro de tendencias alcistas, corto en euforia sobre-extendida.
* **Cautela científica:** el lift de la representación régimen es heterogéneo entre cortes (0.72, 1.9, 6.71, 6.15 — más fuerte en los cortes recientes) y 1 superviviente de 65,536 aún podría ser azar residual. **Validación pendiente antes de la Fase 2:** evaluar la candidata en activos completamente nuevos (bonos TLT, emergentes EEM, divisas) que ningún experimento haya tocado — el out-of-sample definitivo.

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