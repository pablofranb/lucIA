import sys
from pathlib import Path

import streamlit as st


BASE = Path(__file__).resolve().parent.parent
CARPETA_CLASIFICADOR = BASE / "clasificador"
CARPETA_CODIGO = CARPETA_CLASIFICADOR / "src"
CARPETA_MODELO = CARPETA_CLASIFICADOR / "models" / "beto-hipotecas"


@st.cache_resource
def cargar_clasificador():
    if not CARPETA_MODELO.is_dir():
        raise FileNotFoundError(
            f"No encuentro el modelo entrenado en: {CARPETA_MODELO}"
        )

    if str(CARPETA_CODIGO) not in sys.path:
        sys.path.insert(0, str(CARPETA_CODIGO))

    from predict import ClasificadorHipotecas

    return ClasificadorHipotecas(
        carpeta_modelo=CARPETA_MODELO,
    )


def clasificar_mensaje(texto):
    if not texto.strip():
        raise ValueError("No se puede clasificar un mensaje vacío.")

    clasificador = cargar_clasificador()
    resultado = dict(clasificador.predecir([texto])[0])

    if resultado["etiqueta"] == "HIPOTECA":
        resultado["departamento"] = "Hipotecas"
    elif resultado["etiqueta"] == "OTRO":
        resultado["departamento"] = "Atención al cliente"
    else:
        raise ValueError(
            f"Etiqueta desconocida: {resultado['etiqueta']}"
        )

    return resultado