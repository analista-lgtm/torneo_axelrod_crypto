# 🧭 Reflexiones Finales: el Sistema 40/60 y lo que el Laboratorio nos Enseñó sobre los Mercados

*Torneo Axelrod Crypto — informe de cierre para colaboradores (julio 2026)*

*Este documento complementa a [CONCLUSIONES.md](CONCLUSIONES.md) (el cierre técnico-estadístico)
y a [BITACORA.md](BITACORA.md) (la crónica experimento a experimento). Aquí está la síntesis
conceptual: qué construimos, por qué funciona, y las cinco reflexiones sobre la naturaleza de
los mercados que emergieron del camino.*

---

## 1. El sistema final: el Portafolio Institucional 40/60

Después de 15 experimentos y ~1.5 millones de backtests, el único constructo que sobrevivió
todas las pruebas es sorprendentemente simple. Dos componentes:

**Componente A — Motor de tendencia (TSMOM-252): 40% del capital.**
Para cada uno de 18 mercados globales (cripto, índices de EE.UU./Europa/Japón/emergentes,
bonos, oro, plata, cobre, petróleo, gas, maíz, divisas), cada día una sola pregunta:
*¿el precio de hoy es mayor que el de hace 252 sesiones (≈1 año)?*
Mayor → posición larga. Menor → posición corta. Nada más. Sin predicción, sin patrones
complejos: seguir la dirección del último año.

**Componente B — El mercado puro (Buy & Hold diversificado): 60% del capital.**
Los mismos 18 mercados, siempre comprados. Poseer el mundo, de forma equilibrada.

**Las tres reglas de construcción (idénticas en ambos componentes):**
1. **Ponderación por volatilidad inversa** (63 días, causal): el gas natural que se mueve 4%
   diario recibe poco capital; los bonos que se mueven 0.4% reciben más. Ningún mercado
   ruidoso domina.
2. **Costos explícitos**: 10 puntos básicos por cada cambio de señal.
3. **Vol-targeting al 10% anual**: la exposición total se escala según la volatilidad
   reciente del propio portafolio (tope 2x). Más invertido en calma, menos en tormenta.

El peso 40/60 se eligió **honestamente** (solo con datos previos a 2025-07) y la mezcla se
rebalancea mensualmente (el rebalanceo diario no aporta nada: probado).

**Los números (2015-2026, tras costos):**

| | Retorno total | Sharpe | Max DD | t-stat | p-valor |
|---|---|---|---|---|---|
| Mezcla 40/60 | +432% | **1.09** | **−18.9%** | 4.33 | <0.001 |
| B&H diversificado solo | +518% | 1.02 | −27.5% | 4.05 | — |
| TSMOM solo | +292% | 0.78 | −21.1% | 3.10 | 0.0005 |

Y el examen final: en los 12 meses "sagrados" (2025-07 → 2026-07), excluidos de **toda**
decisión, la mezcla rindió **+14.7% con Sharpe 1.20 y drawdown de −6.0%**.

## 2. Por qué funciona: la teoría que lo soporta

Una estrategia sin mecanismo explicable es un patrón estadístico esperando morir. Esta tiene
dos motores teóricos, ambos con décadas de literatura:

**Motor 1 — La prima de tendencia** (Moskowitz, Ooi & Pedersen, *Time Series Momentum*,
Journal of Financial Economics 2012; Hurst, Ooi & Pedersen, *A Century of Evidence on
Trend-Following*, con datos desde 1880):
- *Sub-reacción inicial*: la información nueva se incorpora a los precios gradualmente
  (anclaje, efecto disposición: la gente vende ganadores pronto y aguanta perdedores).
  Las tendencias de meses son ese ajuste lento hacia el nuevo valor justo.
- *Sobre-reacción tardía*: los flujos de manada extienden el movimiento; la señal anual
  captura ambos tramos y sale cuando el signo se invierte.
- *Flujos no especulativos*: bancos centrales, coberturas corporativas y rebalanceos por
  mandato mueven precios sin buscar ganancia, dejando persistencia cosechable.
- *¿Por qué la competencia no la elimina?* Por los **límites del arbitraje**: cosecharla
  exige tolerar años perdedores (2023 y 2026 lo fueron) sin abandonar. Los patrones rápidos
  los mata la velocidad; los lentos sobreviven porque explotarlos duele. La prima de
  tendencia es un pago por paciencia.

**Motor 2 — La diversificación entre fuentes de retorno** (Markowitz, el único almuerzo
gratis): la correlación diaria entre TSMOM y B&H es **0.41**. Dos motores que sufren en
regímenes distintos producen un camino más suave que cualquiera de los dos. Y el mecanismo
es medible: en los 13 peores meses del B&H (promedio −5.1%), el TSMOM promedió **+0.25%** —
porque cuando los mercados caen durante meses, el sistema ya está corto y convierte la
fuente de dolor en ganancia ("crisis alpha"). Por eso el óptimo de mezcla es interior
(cualquier peso entre 10% y 55% de TSMOM queda a ≤0.05 del Sharpe máximo: una meseta
robusta, no un pico frágil).

## 3. Reflexión I — La aleatoriedad del corto plazo no es un mito, pero tiene letra pequeña

El resultado negativo del laboratorio (Exps. 5-11) es una demostración empírica de la
eficiencia de forma débil: probamos el espacio **completo** de reglas sobre patrones diarios
de precio (las 65,536, no una muestra) y no contenía señal. La correlación entre "qué ganó
ayer" y "qué ganará mañana" fue ~0.1 en Bitcoin y **negativa** en Ethereum.

Pero "impredecible para nosotros" no significa "aleatorio":

1. **La aleatoriedad es direccional, no total.** El *signo* del retorno diario es una moneda
   al aire; su *magnitud* no: la volatilidad se agrupa (un día violento anuncia más días
   violentos). Nuestro propio sistema explota esa predecibilidad — los pesos 1/vol y el
   vol-targeting SON pronósticos de volatilidad que funcionan. A corto plazo el mercado no
   dice hacia dónde va, pero sí cuánto se va a mover.
2. **La eficiencia es el resultado de la competencia, no una ley física** (paradoja de
   Grossman-Stiglitz): los patrones cortos no faltan porque el mercado sea un dado, sino
   porque miles de fondos los devoran hasta dejarlos indistinguibles del ruido. Existen
   patrones de milisegundos — pero pertenecen a quien tiene infraestructura HFT.
3. **La predecibilidad crece con el horizonte, y hay una razón matemática:** la señal (deriva)
   crece linealmente con el tiempo; el ruido crece con la raíz cuadrada. A 4 días el ruido
   aplasta todo (murieron los autómatas); a 252 días la señal asoma (TSMOM es significativa).
   El laboratorio midió esa transición empíricamente: ruido total a días, memoria débil a
   meses en índices, señal sólida a un año.

## 4. Reflexión II — El azar no se vence: se le da forma (convexidad)

¿Se puede usar la aleatoriedad como arma — cortar perdedoras, dejar correr ganadoras, y que
el azar produzca las ganadoras espectaculares? La respuesta tiene un teorema y un giro:

- **El teorema (parada opcional):** bajo azar puro, ninguna regla de entrada, salida o
  stop-loss cambia el valor esperado. Los stops solo *reforman la distribución* — cortan la
  cola izquierda a cambio de pagar el *whipsaw* (cada rebote tras un stop es una prima de
  seguro pagada). Con costos, el azar puro solo puede dar pérdida esperada.
- **El giro:** esa misma construcción se vuelve rentable en cuanto existe la más mínima
  persistencia — y demostramos que existe, a 12 meses. "Cortar perdedoras y dejar correr
  ganadoras" implementado con disciplina **es exactamente TSMOM**. El proyecto redescubrió
  este principio tres veces con tres vocabularios: el ADN de consenso de los autómatas
  ("compra pánico, acompaña tendencia"), la representación de régimen, y la intuición de
  gestión de riesgo. Tres caminos, una verdad.
- **La evidencia de la convexidad en nuestros datos:** la mezcla tiene asimetría **+3.4**
  (cola derecha). No predecimos qué mercado explotará al alza; la estructura garantiza estar
  montados cuando alguno lo haga y habernos bajado de los que colapsan. El azar de corto
  plazo deja de estorbar porque el sistema no opera en su territorio.
- **El respaldo académico:** Bessembinder (2018): el ~4% de las acciones generó el 100% de
  la creación neta de riqueza sobre los bonos del tesoro desde 1926 (~2.4% a nivel global).
  Los mercados SON loterías de cola gruesa. La conclusión práctica: el riesgo mortal no es
  tener activos mediocres (se diluyen solos), es **no tener a las ganadoras**.

## 5. Reflexión III — El overfitting es el villano principal, y es cuantificable

La lección más cara del laboratorio, para quien construya estrategias después de nosotros:

- Con 65,536 estrategias, *algo* siempre parece funcionar. La abundancia del espacio de
  búsqueda es la **causa** del overfitting, no la solución. Encontramos "campeonas" con
  +3,780% que eran ruido puro (rendían *peor que el azar* fuera de muestra).
- Ganar en 6 mercados durante la ventana que la selección ya vio no predice nada. Ganar en
  el pasado de un solo mercado tampoco (>99.8% de tasa de overfitting local).
- Las ventajas reales son **débiles** (Sharpe 0.3-0.8 con décadas de datos) y pierden
  segmentos individuales con frecuencia: no se detectan pidiendo "ganar siempre", sino con
  estadística agregada (t-stats, bootstrap) sobre horizontes largos y muchos mercados.
- El antídoto quedó codificado como el **Tribunal de 4 capas**: multi-activo → walk-forward
  multi-corte → jurado de activos vírgenes → período sagrado; con **pre-registro** de una
  única hipótesis primaria tomada de la literatura ANTES de mirar datos. El tribunal condenó
  ~1.5 millones de configuraciones sin mecanismo; su única absolución (TSMOM) significa algo
  precisamente por eso.

## 6. Reflexión IV — Índices, amplitud y ponderación

Un índice ponderado por capitalización es la implementación pasiva perfecta de la Reflexión
II: una máquina automática de dejar correr ganadoras (crecen su peso solas) y encoger
perdedoras (hasta la irrelevancia). De ahí tres consecuencias:

1. **¿Índice amplio o concentrado? (¿MSCI World o S&P 500?)** El S&P rindió más en
   2010-2025; el mundo rindió más en 2000-2010 y en los 70-80 (Japón). Elegir al campeón del
   período pasado es **overfitting geográfico** — el mismo error del Experimento 5 con otra
   ropa. La teoría de colas gruesas favorece la amplitud sin ambigüedad: el índice de 1,400
   empresas en 23 países tiene garantizado el billete ganador de Bessembinder esté donde
   esté; el de 500 empresas de un país apuesta a que saldrá en su territorio.
2. **Nuestra propia evidencia favorece la amplitud:** pasar de 11 a 18 mercados subió el
   t-stat de 1.78 a 3.10. La amplitud no diluyó la señal — la fortaleció. Es la única forma
   de cosechar primas débiles.
3. **Matices honestos:** las correlaciones entre desarrollados son altas (~0.8), así que la
   protección internacional es contra el desastre idiosincrático de un país, no contra un
   bajista global. Y el S&P ya no es tan "500": sus 10 mayores empresas pesan ~35% — el
   mecanismo de dejar correr ganadoras llevado a la concentración.

**Regla de oro:** no elijas al campeón del pasado; elige la estructura que no necesita
adivinar quién será el campeón del futuro.

## 7. Cómo aprovecharlo económicamente

**Tres rutas de implementación (de simple a fiel):**
- **Ruta A — dos ETFs:** el sleeve TSMOM ya existe empaquetado (ETFs de managed futures tipo
  DBMF/KMLM/CTA, ~0.85% anual) + un portafolio pasivo global (ACWI/VT) para el sleeve B&H.
  40/60, rebalanceo mensual. Operable desde montos pequeños con un bróker internacional.
- **Ruta B — señales propias con ETFs:** replicar TSMOM en modo Long/Cash (los cortos con
  ETFs son costosos) usando nuestro código como generador mensual de señales.
- **Ruta C — futuros (la fiel):** micro-futuros dan el TSMOM real con cortos y financiación
  implícita casi gratis; exige más capital (~USD 25-50k) y operación.

**El protocolo conductual (más importante que la ruta):** (1) paper trading 3-6 meses;
(2) empezar con fracción pequeña; (3) escribir ANTES de empezar cuánto drawdown se tolera —
el mayor riesgo de esta estrategia no es financiero sino **conductual**: pierde años
individuales, y quien abandona tras uno malo paga el costo y regala la prima; (4) asesoría
fiscal local. Nada de esto es asesoría financiera personalizada: es el resumen técnico de un
backtest con sus límites declarados.

**Sobre el apalancamiento:** el sistema ya usa apalancamiento endógeno e inteligente (el
vol-targeting sube exposición en calma, tope 2x). Para más, el marco correcto es el Criterio
de Kelly — que era literalmente la Fase 3 del roadmap original. Con Sharpe ~1 y vol 10%,
Kelly completo sugiere niveles absurdos (~10x) porque asume que conoces el Sharpe verdadero
y que no hay colas gruesas; la práctica seria usa ¼-½ de Kelly **dimensionado con el
escenario pesimista** (nuestro IC dice que el Sharpe real podría ser 0.32 → ~1.5x máximo).
Reglas prácticas: apalancar subiendo el vol-target (10% → 15%), no con deuda de margen (que
cuesta 5-6% anual); recordar que a 2x el drawdown histórico de −19% se vuelve ~−35%; y que
la pregunta correcta no es "¿cuánto puedo ganar?" sino "¿qué drawdown soporto sin capitular?"
— de ahí se despeja el apalancamiento, no al revés.

## 8. Cierre: la moraleja Axelrod

El proyecto se llamó "Torneo Axelrod" por los torneos de Robert Axelrod donde la estrategia
ganadora — *Tit for Tat* — resultó ser la más simple del concurso. Nuestro torneo terminó
igual: 65,536 competidoras sofisticadas derrotadas por *"¿subió en el último año? compra;
¿bajó? vende"*, diversificada en 18 mercados y validada con humildad estadística.

La simplicidad no ganó por elegante. Ganó porque es lo único que el ruido no puede imitar.

Empezamos preguntando cómo vencer al azar. Terminamos entendiendo que no se le vence: se le
esquiva operando en el horizonte donde deja de mandar, y se le da forma con convexidad para
que sus sorpresas caigan de nuestro lado. No encontramos magia. Encontramos algo mejor —
**una ventaja real que entendemos.**
