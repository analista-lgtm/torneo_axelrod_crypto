"""
Experimento 11: Familias clásicas de estrategias paramétricas.

En vez de enumerar los 65,536 autómatas posibles (máquina de overfitting),
se definen ~30 estrategias de familias con décadas de evidencia académica:

  - TSMOM (time-series momentum): posición = signo del retorno de los
    últimos k días (Moskowitz, Ooi & Pedersen 2012).
  - Cruce de medias móviles: largo si la media rápida supera a la lenta.
  - Ruptura de canal (Donchian): largo si el cierre supera el máximo de
    los N días previos, corto si perfora el mínimo, plano en el canal.
  - Reversión a la media (RSI de Wilder): largo en sobreventa, corto en
    sobrecompra, plano en zona neutral.
  - Filtro de tendencia largo-plazo: largo sobre la SMA de 100/200 días,
    fuera del mercado debajo (long-only estructural).

Cada estrategia es una función causal df -> Serie de posiciones {-1, 0, +1}
alineada con las filas del df estándar de data_pipeline; la posición del
día t captura Next_Return (el retorno del día siguiente). Los períodos de
calentamiento quedan en 0 (fuera del mercado), nunca mal etiquetados.

Variantes LS (con cortos) y LC (cortos -> fuera del mercado) donde aplica.
"""
import numpy as np
import pandas as pd


def _lc(pos):
    """Variante Long/Cash: las posiciones cortas pasan a estar fuera."""
    return pos.clip(lower=0)


def tsmom(df, k):
    mom = df["Close"] / df["Close"].shift(k) - 1.0
    return pd.Series(np.sign(mom), index=df.index).fillna(0.0)


def cruce_sma(df, rapida, lenta):
    r = df["Close"].rolling(rapida).mean()
    l = df["Close"].rolling(lenta).mean()
    pos = pd.Series(np.where(r > l, 1.0, -1.0), index=df.index)
    pos[l.isna()] = 0.0
    return pos


def donchian(df, n):
    max_prev = df["Close"].shift(1).rolling(n).max()
    min_prev = df["Close"].shift(1).rolling(n).min()
    pos = pd.Series(0.0, index=df.index)
    pos[df["Close"] > max_prev] = 1.0
    pos[df["Close"] < min_prev] = -1.0
    pos[max_prev.isna()] = 0.0
    return pos


def rsi_reversion(df, bajo, alto, periodo=14):
    delta = df["Close"].diff()
    subida = delta.clip(lower=0).ewm(alpha=1 / periodo, adjust=False).mean()
    bajada = (-delta.clip(upper=0)).ewm(alpha=1 / periodo, adjust=False).mean()
    rs = subida / bajada.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    pos = pd.Series(0.0, index=df.index)
    pos[rsi < bajo] = 1.0
    pos[rsi > alto] = -1.0
    pos[rsi.isna()] = 0.0
    return pos


def filtro_sma(df, n):
    sma = df["Close"].rolling(n).mean()
    pos = pd.Series(np.where(df["Close"] > sma, 1.0, 0.0), index=df.index)
    pos[sma.isna()] = 0.0
    return pos


def catalogo():
    """Nombre -> función(df) -> Serie de posiciones."""
    estrategias = {}
    for k in (21, 63, 126, 252):
        estrategias[f"TSMOM-{k}d (LS)"] = lambda df, k=k: tsmom(df, k)
        estrategias[f"TSMOM-{k}d (LC)"] = lambda df, k=k: _lc(tsmom(df, k))
    for r, l in ((5, 20), (10, 50), (20, 100), (50, 200)):
        estrategias[f"SMA {r}/{l} (LS)"] = lambda df, r=r, l=l: cruce_sma(df, r, l)
        estrategias[f"SMA {r}/{l} (LC)"] = lambda df, r=r, l=l: _lc(cruce_sma(df, r, l))
    for n in (20, 55, 100):
        estrategias[f"Donchian-{n}d (LS)"] = lambda df, n=n: donchian(df, n)
        estrategias[f"Donchian-{n}d (LC)"] = lambda df, n=n: _lc(donchian(df, n))
    for bajo, alto in ((30, 70), (20, 80)):
        estrategias[f"RSI {bajo}/{alto} (LS)"] = lambda df, b=bajo, a=alto: rsi_reversion(df, b, a)
        estrategias[f"RSI {bajo}/{alto} (LC)"] = lambda df, b=bajo, a=alto: _lc(rsi_reversion(df, b, a))
    for n in (100, 200):
        estrategias[f"Filtro SMA{n} (LC)"] = lambda df, n=n: filtro_sma(df, n)
    return estrategias
