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

`src/data_pipeline.py` es la capa estándar de ingesta (Yahoo Finance, misma ventana, misma limpieza y codificación para todos los activos) — cualquier análisis nuevo debe consumir datos a través de ella para mantener la comparabilidad.

**Convención canónica de identidad**: el ADN de una estrategia es la cadena binaria donde la posición `s` es la acción para el estado con código `s` ('1' = Long, '0' = Short); el ID es la lectura decimal del ADN (MSB = estado 0).

Ejecutar los scripts de `src/` **desde la raíz del repo** (usan rutas relativas como `data/...`): `python -m src.tournament` o `python src/cross_validation.py`.

Dashboard: `python -m http.server` y abrir `http://localhost:8000` (abre `index.html`; hace `fetch` de los JSON, no funciona como archivo local).

## Advertencias

- `src/tournament.py` y `src/global_quantum_search.py` simulan 65,536 estrategias: tardan varios minutos y consumen bastante RAM. No ejecutarlos como "smoke test" — para verificar cambios basta compilar/importar los módulos.
- `main.py` y los scripts 3-4 requieren internet (APIs de Binance y Yahoo Finance).
- Convención de datos: `Market_State` = 1 si el retorno diario > 0, si no 0; los códigos de estado (`Code_N2/N3/N4`) son la lectura decimal de la secuencia binaria de días, con el día más reciente como bit menos significativo.
