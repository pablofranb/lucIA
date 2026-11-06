from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression


RUTA_DATOS = Path(__file__).resolve().parent / "Risk.xlsx"

NUMERICAS = [
    "age",
    "income",
    "numcards",
    "storecar",
    "loans",
    "numkids",
]

CATEGORICAS = [
    "mortgage",
    "howpaid",
    "marital",
]

VARIABLES = NUMERICAS + CATEGORICAS

# Umbral ilustrativo definido en el cuaderno del equipo.
UMBRAL = 0.60


@st.cache_resource
def preparar_precheck():
    datos = pd.read_excel(RUTA_DATOS, engine="openpyxl")

    faltantes = set(VARIABLES + ["risk"]) - set(datos.columns)
    if faltantes:
        raise ValueError(
            f"Faltan columnas en Risk.xlsx: {sorted(faltantes)}"
        )

    preparacion = ColumnTransformer([
        (
            "numeros",
            Pipeline([
                ("rellenar", SimpleImputer(strategy="median")),
                ("escalar", StandardScaler()),
            ]),
            NUMERICAS,
        ),
        (
            "categorias",
            Pipeline([
                (
                    "rellenar",
                    SimpleImputer(strategy="most_frequent"),
                ),
                (
                    "onehot",
                    OneHotEncoder(
                        drop="first",
                        handle_unknown="infrequent_if_exist",
                    ),
                ),
            ]),
            CATEGORICAS,
        ),
    ])

    modelo = Pipeline([
        ("preparar", preparacion),
        ("regresion_logistica", LogisticRegression(max_iter=2000)),
    ])

    # Reproduce el modelo_final del cuaderno del equipo.
    modelo.fit(datos[VARIABLES], datos["risk"])

    rangos = datos[NUMERICAS].agg(["min", "max"])

    categorias_validas = {
        columna: set(datos[columna].dropna().unique())
        for columna in CATEGORICAS
    }

    return modelo, rangos, categorias_validas


def evaluar_precheck(cliente):
    modelo, rangos, categorias_validas = preparar_precheck()

    faltantes = set(VARIABLES) - set(cliente)
    if faltantes:
        raise ValueError(
            f"Faltan datos del caso: {sorted(faltantes)}"
        )

    fila = pd.DataFrame([cliente])[VARIABLES].copy()

    for columna in NUMERICAS:
        valor = float(fila.at[0, columna])

        if not np.isfinite(valor):
            raise ValueError(f"El dato {columna} no es válido.")

        minimo = float(rangos.loc["min", columna])
        maximo = float(rangos.loc["max", columna])

        if not minimo <= valor <= maximo:
            return {
                "probabilidad": None,
                "supera_umbral": None,
                "mensaje": (
                    f"No se puede estimar este caso: {columna} "
                    f"está fuera del rango de los datos "
                    f"({minimo:g} a {maximo:g})."
                ),
            }

        fila.at[0, columna] = valor

    for columna in CATEGORICAS:
        if fila.at[0, columna] not in categorias_validas[columna]:
            raise ValueError(
                f"El valor de {columna} no aparece en los datos del modelo."
            )

    posicion_buen_riesgo = list(modelo.classes_).index(1)
    probabilidad = float(
        modelo.predict_proba(fila)[0, posicion_buen_riesgo]
    )

    supera = probabilidad >= UMBRAL

    if supera:
        mensaje = (
            "El caso supera el umbral orientativo del modelo de prueba."
        )
    else:
        mensaje = (
            "El caso no supera el umbral orientativo del modelo de prueba."
        )

    return {
        "probabilidad": probabilidad,
        "supera_umbral": supera,
        "mensaje": (
            mensaje
            + " No supone una aprobación ni una denegación de hipoteca."
        ),
    }