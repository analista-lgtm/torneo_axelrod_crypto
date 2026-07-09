# 📖 Bitácora del Laboratorio: la historia de una cacería

*Torneo Axelrod Crypto — crónica científica de los Experimentos 5 a 10 (julio 2026)*

---

## El punto de partida

El proyecto nació con una idea elegante: codificar el mercado como memoria binaria
(día que sube = 1, día que baja = 0) y hacer competir a **todas** las estrategias
posibles — 65,536 con memoria de 4 días — al estilo de los torneos evolutivos de
Robert Axelrod. Los primeros experimentos sobre Bitcoin encontraron campeonas con
retornos de +3,780%. Parecía un tesoro.

El Experimento 4 dio la primera señal de alarma: la campeona de Bitcoin, llevada a
Ethereum, destruyó el −79% de la cuenta. Overfitting. La pregunta que definió todo
lo que siguió: **¿cómo se distingue una estrategia real de un espejismo estadístico?**

## Capítulo 1 — El torneo multi-activo (Exp. 5)

Corrimos los 3 experimentos (16, 256 y 65,536 estrategias) de forma independiente
en 6 mercados con regímenes opuestos: Bitcoin (+66% en la ventana), Ethereum (−32%),
S&P 500 (+84%), Oro (+123%), Petróleo (−4%) y el Dólar (+9%). Con una tubería de
datos estandarizada para que nada fuera atribuible a sesgos de preparación.

**Hallazgos:** el overfitting local superó el **99.8%** en todos los mercados
(de las 10,019 campeonas de BTC, 6 sobrevivían fuera de casa). Pero aparecieron
**14 estrategias "universales"** — positivas en los 6 mercados a la vez — agrupadas
en 5 familias de ADN casi idéntico, con una filosofía interpretable: comprar pánico
extremo, vender el rebote falso, acompañar la tendencia. El modo Long/Cash demostró
mejorar Sharpe y drawdown del mismo ADN (10 de 10 casos) a cambio de retorno máximo.

## Capítulo 2 — La prueba del tiempo (Exp. 6)

La robustez entre activos no garantiza robustez temporal. Seleccionamos la élite
usando solo 2021-2024 y la evaluamos en 2024-2026, con la métrica del **lift**
(supervivencia vs. azar).

**Veredicto: overfitting temporal total.** De 371 universales del train, **cero**
sobrevivieron el test (el azar predecía ~2). Peor: la élite del pasado rindió *por
debajo* del azar (lift 0.03) — los patrones ganadores tendían a revertirse. Las 14
universales del Capítulo 1 eran artefactos in-sample.

## Capítulo 3 — El duelo de representaciones (Exp. 7)

Si las secuencias diarias exactas son ruido, quizás otra codificación del mercado
contenga señal. Cuatro representaciones causales compitieron bajo walk-forward de
**4 cortes temporales**: la secuencia original (control), signo+magnitud, secuencia
semanal y **régimen** (precio vs. SMA20, SMA20 vs. SMA50, volatilidad, día).

**Resultado:** control, magnitud y semanal murieron (lift ~0). La de régimen mostró
vida: lift promedio 3.87× y **una superviviente de los 4 cortes** (ID 52982), con
lógica coherente: corto en tendencia bajista volátil, largo en retrocesos alcistas,
corto en euforia.

## Capítulo 4 — El jurado virgen (Exp. 8)

La candidata y sus 2 vecinas de familia enfrentaron 5 mercados que ninguna selección
había tocado: bonos, emergentes, Nikkei, plata, dólar/yen.

**Veredicto: 0 de 3 aprueban** (lift 0). Matiz honesto: la 52982 no colapsó — ganó
fuerte en 3 de 5 (+154% EEM) y perdió poco en 2 (−7%) — el mejor perfil del
proyecto, pero por debajo del estándar.

## Capítulo 5 — ¿Existen los especialistas? (Exp. 9)

Hipótesis legítima: los mercados son distintos; una estrategia puede ser rentable
solo en el suyo. Eliminamos la exigencia cruzada y medimos si las campeonas de cada
mercado repiten en su propio futuro (lift local + correlación de Spearman del
ranking completo entre períodos).

**El giro irónico:** la especialización existe, pero al revés de lo esperado. Los
mercados con memoria son los **índices bursátiles** (S&P 500: Spearman 0.41; Nikkei:
0.27) y las tasas. Las criptomonedas — donde nació el proyecto — no tienen ninguna
(BTC: 0.11; ETH: **−0.11**, sus ganadoras del pasado tienden a perder).

## Capítulo 6 — El portafolio y el período sagrado (Exp. 10)

La síntesis: un portafolio donde cada componente sobrevive en su terreno
(universales + especialistas por mercado), con la capa metodológica definitiva:
un **período sagrado** — los últimos 12 meses, intocados por toda selección — como
examen final equivalente a operar en vivo.

**Veredicto:** la pista universal produjo 0 supervivientes. 10 de 11 mercados
produjeron especialistas de selección (miles, sospechosamente abundantes donde el
B&H era plano — sesgo corto disfrazado de habilidad). El portafolio rindió
**−1.71%** en el año sagrado contra **+18.51%** de sus mismos pesos en Buy & Hold.

## El resultado del laboratorio

Tras ~1.5 millones de backtests (65,536 estrategias × 4 representaciones × 2 modos
× 11 mercados × múltiples cortes), la conclusión es un **no-resultado robusto**,
que es el tipo de resultado más difícil de obtener honestamente:

> **Los autómatas fijos de estados diarios no contienen ventaja explotable que
> sobreviva a un período genuinamente no visto — ni como universales, ni como
> especialistas, ni en portafolio.**

La memoria débil detectada en índices (Spearman ≤ 0.41) es real pero insuficiente
para seleccionar estrategias individuales a esta granularidad.

## El verdadero activo: el Tribunal de 4 capas

Lo que queda construido y es reutilizable para cualquier hipótesis futura:

1. **Multi-activo** — la señal debe existir en mercados con regímenes opuestos.
2. **Walk-forward multi-corte** — debe persistir sin importar dónde se corte la historia.
3. **Jurado virgen** — debe generalizar a mercados que jamás participaron en la selección.
4. **Período sagrado** — debe ganar en un tramo final que nadie vio, como en vivo.

Con la métrica del **lift** (¿supera al azar?) como juez en cada capa. Ninguna
estrategia amateur sobrevive las 4 capas por suerte.

## Lecciones para quien lea esto

- Con 65,536 intentos, *algo* siempre parece funcionar. La abundancia del espacio de búsqueda es la causa del overfitting, no la solución.
- Ganar en 6 mercados durante la ventana que la selección ya vio no predice nada: la única prueba es el tiempo no visto.
- Los mercados difieren en cuánta memoria tienen — y las criptos son las que menos.
- Un resultado negativo con estándar alto vale más que mil backtests espectaculares.
