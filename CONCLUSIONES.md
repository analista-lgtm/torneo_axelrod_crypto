# 📜 Conclusiones del Laboratorio

*Torneo Axelrod Crypto Engine — documento técnico de cierre (julio 2026)*
*Audiencia: profesionales de finanzas cuantitativas y estadística. La crónica narrativa está en [BITACORA.md](BITACORA.md); el detalle por experimento en [ROADMAP.md](ROADMAP.md).*

---

## Resumen ejecutivo

Tras 15 experimentos y ~1.5 millones de backtests bajo un protocolo anti-overfitting de
cuatro capas, el laboratorio establece dos resultados — uno negativo y uno positivo — y
ambos con el mismo estándar de evidencia:

1. **Resultado negativo (Exps. 5-11):** el espacio completo de autómatas binarios de
   estados diarios (65,536 estrategias × 4 representaciones × 2 modos de ejecución ×
   11 mercados) **no contiene ventaja explotable** que sobreviva a datos genuinamente
   no vistos — ni como estrategias universales, ni como especialistas por mercado, ni
   agregadas en portafolio. Las tasas de overfitting superaron el 99.8% y las élites
   seleccionadas in-sample rindieron *por debajo* del azar fuera de muestra.

2. **Resultado positivo (Exps. 12-15):** existe una **prima de tendencia de series
   temporales (time-series momentum)** débil pero estadísticamente robusta, cosechable
   únicamente mediante diversificación multi-activo con paridad de riesgo, y cuya mezcla
   con exposición pasiva produce un portafolio superior en riesgo-ajuste a ambos
   componentes. Este constructo es el único del laboratorio que aprobó el período
   sagrado (12 meses finales excluidos de toda decisión).

---

## El hallazgo positivo, en cifras

**Señal:** TSMOM-252 — posición larga (corta) en cada mercado si su retorno acumulado de
las últimas 252 sesiones es positivo (negativo). Pre-registrada como hipótesis primaria
(Moskowitz, Ooi & Pedersen, *Time Series Momentum*, JFE 2012) antes de ejecutar cálculo
alguno; ninguna búsqueda ni optimización participó en su elección.

**Construcción:** 18 mercados (cripto, índices de EE.UU./Europa/Japón/emergentes, bonos,
metales, energía, agrícolas, divisas), ventana 2015-07 → 2026-07, ponderación por
volatilidad inversa (63d, causal), costos de 10 pb por cambio de señal, vol-targeting
del portafolio al 10% anual (causal, apalancamiento ≤ 2x).

| Constructo | Retorno total | Sharpe | Max DD | t-stat | p (bootstrap) |
|---|---|---|---|---|---|
| TSMOM-252 diversificado | +292% | 0.78 | −21.1% | 3.10 | **0.0005** |
| B&H diversificado (mismos pesos) | +518% | 1.02 | −27.5% | 4.05 | — |
| **Mezcla 40/60 TSMOM/B&H** | **+432%** | **1.09** | **−18.9%** | **4.33** | **<0.001** |

- IC 95% (bootstrap por bloques de 10d, 2,000 remuestreos) del Sharpe de TSMOM-252:
  **[0.32, 1.26] — excluye el cero tras costos.**
- Variantes secundarias TSMOM-126 (p=0.0035) y SMA 50/200 (p=0.0005) también
  significativas tras Bonferroni (α=0.0125): la robustez es de la *familia* de
  tendencia, no de una parametrización.
- Correlación diaria TSMOM ↔ B&H: **0.41** → el óptimo de mezcla es interior
  (frontera con máximo en w ≈ 25-40% TSMOM) y es una **meseta**: cualquier
  w ∈ [10%, 55%] queda a ≤ 0.05 del Sharpe máximo.

**Validación fuera de muestra (período sagrado, 2025-07 → 2026-07, excluido de toda
selección incluida la del peso de mezcla):** la mezcla con w\*=40% — elegido solo con
datos previos — rindió **+14.7%, Sharpe 1.20, Max DD −6.0%**.

**Implementabilidad:** rebalanceo mensual o trimestral entre componentes cuesta ~0.01 de
Sharpe frente al diario. **Crisis alpha medido:** en el peor decil de meses del B&H
(13 meses, media −5.1%), TSMOM promedió +0.25% y la mezcla −3.0%. Colas de la mezcla:
Sortino 1.94, asimetría **+3.4**, peor mes −7.7%, 61% de meses positivos.

---

## Por qué funciona: mecanismo económico

Una anomalía sin mecanismo es un artefacto en espera de desaparecer. El momentum de
series temporales tiene tres soportes documentados:

1. **Sub-reacción inicial:** la información se incorpora a precios gradualmente
   (anclaje, efecto disposición); las tendencias de meses son el ajuste lento hacia el
   nuevo valor.
2. **Sobre-reacción tardía:** los flujos de manada extienden el movimiento más allá del
   valor justo; la señal de 12 meses captura ambos tramos y sale cuando el signo anual
   se invierte.
3. **Flujos no especulativos:** coberturas corporativas, bancos centrales y rebalanceos
   por mandato mueven precios sin buscar ganancia, creando persistencia cosechable.

La mezcla con B&H funciona por diversificación pura: dos fuentes de retorno con
correlación 0.41 que sufren en regímenes distintos — el TSMOM se pone corto durante los
mercados bajistas prolongados y convierte la fuente de dolor del B&H en ganancia
(verificado empíricamente en el peor decil de meses).

**Continuidad con la intuición original del proyecto:** el "ADN de consenso" de los
autómatas (Exp. 5) ya describía comprar pánico sostenido y acompañar tendencias; el
Exp. 9 localizó la única memoria real de los mercados en los horizontes de tendencia.
La hipótesis fundacional era correcta en su dirección — el error estaba en el
microscopio: a 4 días la tendencia es ruido; a 12 meses es señal.

---

## Por qué el resultado es creíble: la cadena de inferencia

1. **Pre-registro** de la hipótesis primaria (sin búsqueda → el p-valor es interpretable).
2. **Significancia tras costos** (t=3.10; bootstrap por bloques que preserva la
   autocorrelación; IC del Sharpe excluye 0).
3. **Corrección por comparaciones múltiples** en las secundarias (Bonferroni).
4. **Robustez paramétrica** (familia de señales y meseta del peso de mezcla).
5. **Selección honesta + período sagrado** (el peso se eligió sin acceso a los 12 meses
   finales; el constructo los aprobó con Sharpe 1.20).
6. **Plausibilidad externa** (Sharpe consistente con 50+ años de literatura y con la
   industria de managed futures; no sospechosamente alto).
7. **Poder negativo demostrado del protocolo:** las mismas cuatro capas (multi-activo →
   walk-forward multi-corte → jurado virgen → período sagrado) ejecutaron sin excepción
   a las ~1.5 millones de configuraciones sin mecanismo. Un tribunal que condena todo lo
   falso da significado a su única absolución.

## Limitaciones declaradas

- **Intermitencia:** la prima pierde años individuales (2023, 2026 parcial); exige
  horizonte de tenencia de años, no meses.
- **Ventana:** 11 años es corto frente al estándar académico (50+); la magnitud del
  Sharpe futuro probablemente sea menor que la histórica (sesgo de publicación +
  estimación).
- **Datos:** Yahoo Finance con futuros continuos y auto-ajuste; una implementación real
  exige datos de ejecución de calidad institucional.
- **Costos:** 10 pb por rotación es razonable para ETFs/futuros líquidos pero no
  incluye deslizamiento en mercados estresados ni costos de financiación del
  apalancamiento del vol-targeting.
- **Replicación externa pendiente** al cierre de este documento.

## Conclusión

El laboratorio cumplió su objetivo doble: demostró con el estándar más alto que las
"estrategias mágicas" de patrones diarios no existen, y aisló, verificó y hizo operable
la única fuente de retorno activa que sobrevivió a todos los tests — la prima de
tendencia diversificada. El portafolio institucional resultante (25-40% TSMOM
multi-activo + 60-75% B&H diversificado, rebalanceo mensual) es modesto, explicable,
estadísticamente defendible y aprobó su examen final en datos que ninguna decisión tocó.

*En una frase: no encontramos magia; encontramos algo mejor — una ventaja real que
entendemos.*
