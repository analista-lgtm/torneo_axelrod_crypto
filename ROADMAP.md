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

### 🏛️ Experimento 11: Familias Clásicas ante el Tribunal — Completado
* **Objetivo:** Nueva forma de crear estrategias: en vez de enumerar 65,536 autómatas sin prior, **28 estrategias paramétricas de familias con evidencia académica** — momentum TSMOM (21-252d), cruces de SMAs, rupturas Donchian, reversión RSI y filtros de tendencia — juzgadas con la arquitectura del Exp. 10 (selección walk-forward de 4 cortes + período sagrado). Con 28 hipótesis en vez de 65,536, el riesgo de superviviente-por-azar cae tres órdenes de magnitud.
* **Implementación:** `src/classic_strategies.py` (generadores causales) + `src/classic_lab.py`. Resultados en `data/multi_activo/clasicas.json` y pestaña "🏛️ Clásicas" del dashboard.
* **Resultados:** Pista universal: **0 supervivientes**. Pista especialista: solo 2 mercados producen supervivientes (TLT → RSI 30/70; USDJPY → SMA 5/20, con 2 cada uno). El mini-portafolio resultante quedó plano en el sagrado (−0.1% vs +5.3% de su benchmark).
* **Lección metodológica importante:** ni siquiera TSMOM-252 — la anomalía con más evidencia académica — pasa el criterio de "ganar en train Y test de los 4 cortes". Esto revela algo sobre el estándar, no solo sobre las estrategias: **las ventajas reales que existen en mercados son débiles** (Sharpe 0.3-0.8 con décadas de datos y cientos de mercados) y una ventaja débil pierde segmentos individuales con frecuencia — no puede aprobar un criterio de "ganar siempre en todas las ventanas". El tribunal actual detecta ventajas fuertes (que probablemente no existen); detectar ventajas débiles requiere tests estadísticos agregados (t-stats sobre horizontes largos y muchos mercados a la vez), no supervivencia segmento a segmento.

### 🌐 Experimento 12: El Meta-Portafolio Estadístico — Completado ⭐
* **Cambio de instrumento (lección del Exp. 11):** las ventajas reales son débiles y no aprueban criterios de "ganar siempre"; el instrumento correcto es la agregación estadística. Reglas fijadas **a priori** desde la literatura (sin selección → sin sesgo de selección), aplicadas a los 11 mercados a la vez con paridad de riesgo (1/vol 63d). Variante primaria pre-registrada: **TSMOM-252** (Moskowitz, Ooi & Pedersen 2012); secundarias con corrección de Bonferroni. Inferencia con t-stat y bootstrap por bloques (10d × 2,000).
* **Implementación:** `src/meta_portfolio.py`, resultados en `data/multi_activo/meta_portafolio.json` y pestaña "🌐 Meta-Portafolio" del dashboard.
* **Resultado: ⭐ LA PRIMERA SEÑAL ESTADÍSTICAMENTE SIGNIFICATIVA DE LA CAMPAÑA.**
  * **TSMOM-252 diversificado: +141.4% total, Sharpe 0.67, Max DD −25.0%, t-stat 1.78, p(bootstrap) = 0.0355** — significativa al 5% (unilateral). Positiva en 2022 (+11.5%, año en que el B&H diversificado sufría), 2023, 2024 (+67.7%) y 2025 (+29.5%).
  * Frente al B&H diversificado (+166.4%, Sharpe 0.65, DD −34.5%): retorno similar ajustado por riesgo con **drawdown un tercio menor** y ganancias en el año bajista — el perfil clásico de "crisis alpha" del trend-following.
  * Secundarias: ninguna sobrevive Bonferroni (Donchian-100 la más cercana, p=0.0715). El ensamble: Sharpe 0.53, p=0.079.
* **Cautelas honestas:** (1) el CI95 bootstrap del Sharpe roza el cero ([−0.07, 1.44]) — evidencia moderada, no prueba; (2) ventana de 5 años es corta para una ventaja débil (la literatura usa 50+ años); (3) sin costos de transacción, aunque TSMOM-252 rota poco (pocas señales por año y mercado), el impacto sería menor; (4) el período sagrado quedó plano (−0.01%) — 2026 fue un mal semestre para tendencia (−14%), coherente con el carácter intermitente de la anomalía.
* **Por qué este resultado es creíble donde los anteriores no:** una sola hipótesis primaria declarada antes de mirar los datos, con 50 años de literatura detrás, sin ningún proceso de selección — el p-valor significa lo que dice. La campaña completa (Exps. 5-12) cuenta ahora una historia coherente: no hay reglas mágicas individuales, pero sí una prima débil de tendencia, cosechable únicamente vía diversificación masiva y paciencia.

### 🌐 Experimento 13: Meta-Portafolio v2 (extendido) — Completado ⭐⭐
* **Objetivo:** someter la señal del Exp. 12 a las cuatro pruebas que la refuerzan o la refutan: el doble de historia (2015-2026), más diversificación (18 mercados: se añaden cobre, maíz, gas natural, EFA, Russell 2000, EUR/USD y DAX), **costos explícitos** (10 pb por rotación) y **vol-targeting** al 10% anual (causal, tope 2x).
* **Implementación:** `src/meta_portfolio_v2.py`, resultados en `data/multi_activo/meta_portafolio_v2.json`, selector de versión en la pestaña "🌐 Meta-Portafolio".
* **Resultado: LA EVIDENCIA SE FORTALECE DECISIVAMENTE (ya con costos):**
  * **TSMOM-252 (primaria): +292.1%, Sharpe 0.78, Max DD −21.1%, t-stat 3.10, p(boot) = 0.0005, Sharpe CI95 [0.32, 1.26]** — el intervalo de confianza ya **excluye el cero**.
  * **TSMOM-126 (p=0.0035) y SMA 50/200 (p=0.0005) también sobreviven Bonferroni** (α=0.0125): es la *familia* de tendencia la que es robusta, no una parametrización afortunada. Donchian-100 no pasa (p=0.0645).
  * **Ensamble (voto): Sharpe 0.78 con el menor drawdown de todos (−15.5%)** — la combinación de señales suaviza sin sacrificar retorno.
* **Lectura honesta:** el B&H diversificado con vol-target rindió más en esta década alcista (+518%, Sharpe 1.02). El valor del trend-following no es "ganarle al B&H en mercados alcistas" sino: drawdown estructuralmente menor, ganancias en años bajistas (2022) y baja correlación — es un **diversificador con ventaja propia estadísticamente robusta**, no un reemplazo del mercado. El período sagrado reciente sigue flojo (+1.2%), coherente con la intermitencia de la anomalía.
* **Estado de la línea:** con p=0.0005 tras costos y 11 años, la prima de tendencia diversificada queda establecida como el primer (y único) hallazgo positivo validado del laboratorio. Extensiones posibles: allocation combinada TSMOM + B&H (el "portafolio institucional"), rebalanceo mensual, y datos aún más largos por mercado.

### 🏦 Experimento 14: El Portafolio Institucional — Completado
* **Pregunta:** con la prima de tendencia establecida (Exp. 13), la decisión práctica no es "¿TSMOM o B&H?" sino **"¿cuánto de cada uno?"**. Si la correlación es moderada, la mezcla debe superar en riesgo-ajuste a ambos componentes (el único almuerzo gratis de las finanzas).
* **Implementación:** `src/institutional_blend.py` (mezclas 0/25/50/75/100% TSMOM-252 vs B&H diversificado, misma infraestructura del Exp. 13), resultados en `data/multi_activo/institucional.json` y pestaña "🏦 Institucional".
* **Resultados (2015-2026, correlación diaria TSMOM↔B&H = 0.41):**
  | Mezcla | Retorno | Sharpe | Max DD | t-stat |
  |---|---|---|---|---|
  | 100% B&H | +518% | 1.02 | −27.5% | 4.05 |
  | **25% TSMOM / 75% B&H** 🏆 | +465% | **1.09** | −21.8% | **4.32** |
  | 50% TSMOM / 50% B&H | +409% | 1.07 | **−17.4%** | 4.25 |
  | 100% TSMOM | +292% | 0.78 | −21.1% | 3.10 |
* **Veredicto: la diversificación funciona — el óptimo es interior, no un extremo.** La mezcla 25/75 logra el mejor Sharpe (1.09) y la 50/50 recorta el drawdown de −27.5% a −17.4% manteniendo Sharpe superior al B&H puro. Añadir el trend-following al portafolio pasivo mejora el riesgo-ajuste aunque el TSMOM aislado rinda menos: exactamente lo que predice la teoría de portafolios con correlación 0.41.
* **Estado del proyecto:** la línea de investigación queda madura y con conclusión práctica accionable. Extensiones futuras: rebalanceo mensual con bandas, replicación independiente externa (en curso con LLM auditor), y actualización periódica de datos.

### 🛠️ Experimento 15: Implementabilidad y Robustez — Completado ⭐ (aprueba el sagrado)
* **Objetivo:** las cuatro preguntas que separan un backtest bonito de algo operable, aplicadas al portafolio institucional del Exp. 14.
* **Implementación:** `src/implementation_check.py`, resultados en `data/multi_activo/implementacion.json`, panel integrado en la pestaña "🏦 Institucional".
* **Resultados:**
  1. **Robustez del peso:** Sharpe(w) es una **meseta** (w ∈ [10%, 55%] queda a ≤0.05 del máximo), no un pico frágil. El w* elegido **solo con la ventana de selección** (sin mirar el futuro) es 40% TSMOM.
  2. **⭐ Examen sagrado aprobado:** la mezcla 40/60 con peso elegido honestamente rindió **+14.7% con Sharpe 1.20 y drawdown de solo −6.0%** en los 12 meses que ninguna decisión tocó — el primer constructo del laboratorio que pasa el examen final con nota.
  3. **Rebalanceo realista:** mensual o trimestral pierde ~0.01 de Sharpe frente al diario (1.08-1.09 en todos los casos) — totalmente implementable en la práctica.
  4. **Crisis alpha medido:** en los 13 peores meses del B&H (promedio −5.1%), el TSMOM promedió **+0.25%** y la mezcla amortiguó la pérdida a −3.0% (42% menos dolor).
  5. **Colas sanas:** Sortino 1.94, asimetría **positiva** (+3.4, cola derecha), peor mes −7.7%, 61% de meses positivos.
* **Estado:** la línea TSMOM + B&H queda validada de punta a punta: significancia estadística tras costos (Exp. 13), óptimo de mezcla interior (Exp. 14), robustez paramétrica, implementabilidad práctica y aprobación del período sagrado (Exp. 15). Pendiente: la replicación independiente externa (en curso) como sello final.

### 🌡️ Tablero de Volatilidad — Fase 1 Completada (línea nueva de investigación)
* **Motivación:** la volatilidad es la única variable del laboratorio con predecibilidad demostrada (se agrupa en regímenes; R² de 0.5-0.7 a horizonte diario es alcanzable, contra ~0 de la dirección). Nueva línea: monitorearla, modelarla y usarla para mejorar el vol-targeting del portafolio institucional.
* **Implementación Fase 1 (monitoreo):** `src/vol_monitor.py` + pestaña "🌡️ Volatilidad" del dashboard. `data_pipeline` extendida para conservar OHLC. Métricas por mercado: vol realizada 5/21/63/252d, estimadores eficientes Parkinson y **Yang-Zhang**, EWMA (RiskMetrics λ=0.94), **vol-of-vol**, percentil histórico (semáforo de régimen), estructura temporal 5d/63d (detector de shocks), efecto apalancamiento. Métricas de sistema: correlación media rodante (126d), **absorption ratio** (PCA), % de mercados en vol alta. Implícitas públicas: VIX/OVX/GVZ y prima de riesgo de volatilidad del S&P. Sistema de alertas automáticas.
* **Fase 2 — Torneo de modelos de pronóstico: Completada. Ganador: GJR-GARCH.**
  * **Implementación:** `src/vol_forecast_lab.py` — pronóstico de varianza a 1 día (proxy: retorno²), QLIKE, walk-forward expansivo con re-estimación trimestral, Diebold-Mariano contra HAR, sagrado aparte. Contendientes: HIST-21 y EWMA (varas), HAR-RV (primaria), GJR-GARCH, LightGBM con features cross-mercado.
  * **Resultados (QLIKE promedio selección | sagrado):** GJR-GARCH **1.569 | 1.659** 🏆 (mejor en 12 de 18 mercados, DM significativo sobre HAR en 9) · EWMA 1.588 | 1.661 (gana en 5 — el subcampeón robusto y barato) · HAR estable en 16 de 18 pero con 2 episodios de inestabilidad numérica pese a winsorización (oro, bonos) · HIST-21 1.640 | 1.701 (no gana en ninguno: **la volatilidad ES predecible**) · LightGBM 7.15 (derrota clara del ML).
  * **Lecciones:** (1) el efecto apalancamiento del GJR es ventaja real y consistente; (2) HAR — la primaria pre-registrada — brilla en la literatura con datos intradía, pero con proxies diarios ruidosos la estructura recursiva del GARCH es superior: un hallazgo práctico honesto; (3) a frecuencia diaria, el ML con 8 features pierde contra un modelo de 4 parámetros — la estructura vence a la flexibilidad cuando los datos son ruidosos.
* **Fase 3 — Integración (Exp. 16, pendiente):** sustituir la vol rodante 63d del vol-targeting del 40/60 por el pronóstico GJR-GARCH (con EWMA de respaldo) y medir si el Sharpe mejora (Moreira & Muir 2017 sugiere que sí).

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