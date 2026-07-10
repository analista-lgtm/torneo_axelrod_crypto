"""
Fase 1.5: Representaciones alternativas del estado de mercado.

El Experimento 6 demostró que los estados binarios de secuencias diarias
exactas no persisten en el tiempo. Este módulo define codificaciones
alternativas del mercado; todas son estrictamente causales: el estado del
día t se calcula solo con información disponible al cierre de t (medias
móviles, medianas rodantes y volatilidades usan únicamente el pasado).

Cada representación transforma el DataFrame estándar de data_pipeline en
uno con columnas [Date, Code, Next_Return], donde Code es el estado
decimal (0 .. n_estados-1) y Next_Return el retorno del período siguiente
que captura la estrategia.
"""
import numpy as np
import pandas as pd


def rep_secuencia_n4(df):
    """Línea base (Experimento 5/6): secuencia binaria de 4 días. 16 estados."""
    out = df[["Date", "Code_N4", "Next_Return"]].rename(columns={"Code_N4": "Code"})
    return out.dropna().reset_index(drop=True)


def rep_magnitud_2d(df):
    """
    Signo + magnitud, memoria de 2 días. 16 estados.
    Cada día aporta 2 bits: (subió/bajó, movimiento grande/pequeño), donde
    "grande" = |retorno| mayor que su mediana rodante de 63 días.
    Hipótesis: la magnitud distingue pánico/euforia de ruido, algo que el
    signo puro no ve.
    """
    d = df.copy()
    mediana63 = d["Return"].abs().rolling(63).median()
    signo = (d["Return"] > 0).astype(int)
    magnitud = (d["Return"].abs() > mediana63).astype(int)
    dia = signo * 2 + magnitud                       # 0..3
    d["Code"] = dia.shift(1) * 4 + dia               # memoria de 2 días -> 0..15
    # excluir el calentamiento: sin mediana rodante no hay estado válido
    valido = mediana63.notna() & mediana63.shift(1).notna()
    d = d[valido].dropna(subset=["Code", "Next_Return"])
    d["Code"] = d["Code"].astype(int)
    return d[["Date", "Code", "Next_Return"]].reset_index(drop=True)


def rep_regimen(df):
    """
    Régimen de mercado, sin secuencias. 16 estados.
    4 características binarias del día t:
      bit 3: precio por encima de su media móvil de 20 días
      bit 2: media de 20 por encima de la media de 50 (tendencia de fondo)
      bit 1: volatilidad de 20 días por encima de su mediana rodante anual
      bit 0: el día cerró al alza
    Hipótesis: los regímenes (tendencia + volatilidad) cambian más lento
    que las secuencias exactas y podrían persistir entre períodos.
    """
    d = df.copy()
    sma20 = d["Close"].rolling(20).mean()
    sma50 = d["Close"].rolling(50).mean()
    vol20 = d["Return"].rolling(20).std()
    vol_med = vol20.rolling(252).median()
    f3 = (d["Close"] > sma20).astype(int)
    f2 = (sma20 > sma50).astype(int)
    f1 = (vol20 > vol_med).astype(int)
    f0 = (d["Return"] > 0).astype(int)
    d["Code"] = f3 * 8 + f2 * 4 + f1 * 2 + f0
    # excluir el calentamiento: comparar contra NaN etiquetaría mal el estado
    valido = sma50.notna() & vol_med.notna()
    d = d[valido].dropna(subset=["Code", "Next_Return"])
    d["Code"] = d["Code"].astype(int)
    return d[["Date", "Code", "Next_Return"]].reset_index(drop=True)


def rep_semanal_n3(df):
    """
    Secuencia binaria de 3 SEMANAS. 8 estados.
    Igual que la línea base pero en horizonte semanal: las velas se agregan
    a cierres de viernes y la estrategia decide la posición de la semana
    siguiente. Hipótesis: el ruido diario desaparece y los patrones de
    horizonte largo podrían ser más estables.
    """
    w = df.set_index("Date")["Close"].resample("W-FRI").last().dropna()
    ret = w.pct_change()
    estado = (ret > 0).astype(int)
    code = estado.shift(2) * 4 + estado.shift(1) * 2 + estado
    out = pd.DataFrame(
        {"Date": w.index, "Code": code.values, "Next_Return": ret.shift(-1).values}
    ).dropna()
    out["Code"] = out["Code"].astype(int)
    return out.reset_index(drop=True)


REPRESENTACIONES = {
    "secuencia_n4": {
        "nombre": "Secuencia diaria N=4 (línea base)",
        "fn": rep_secuencia_n4,
        "n_estados": 16,
        "hipotesis": "Control: la representación que falló el Experimento 6.",
    },
    "magnitud_2d": {
        "nombre": "Signo + magnitud (2 días)",
        "fn": rep_magnitud_2d,
        "n_estados": 16,
        "hipotesis": "La magnitud del movimiento (vs. mediana rodante 63d) separa pánico/euforia del ruido.",
    },
    "regimen": {
        "nombre": "Régimen (tendencia + volatilidad)",
        "fn": rep_regimen,
        "n_estados": 16,
        "hipotesis": "Los regímenes cambian más lento que las secuencias y podrían persistir en el tiempo.",
    },
    "semanal_n3": {
        "nombre": "Secuencia semanal N=3",
        "fn": rep_semanal_n3,
        "n_estados": 8,
        "hipotesis": "El horizonte semanal elimina el ruido diario.",
    },
}
