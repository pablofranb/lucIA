import sys
from pathlib import Path

import streamlit as st

BASE = Path(__file__).resolve().parent
CARPETA_PROYECTO = BASE / "Preguntas_frecuentes"
CARPETA_RAG = CARPETA_PROYECTO / "rag"

if str(CARPETA_RAG) not in sys.path:
    sys.path.insert(0, str(CARPETA_RAG))

from embeddings import cargar_modelo
from rag import preparar_indice, recuperar, responder, cargar_secciones


@st.cache_resource
def preparar_buscador():
    nombre_modelo = "intfloat/multilingual-e5-small"
    modelo = cargar_modelo(nombre_modelo)

    chunks, vectores = preparar_indice(
        CARPETA_PROYECTO / "datos",
        CARPETA_PROYECTO / "indice",
        modelo,
        nombre_modelo,
    )

    if not chunks:
        raise ValueError("No se ha extraído contenido de los documentos.")

    return modelo, chunks, vectores


def buscar_documentos(pregunta):
    modelo, chunks, vectores = preparar_buscador()
    return recuperar(pregunta, chunks, vectores, modelo)


def responder_consulta(pregunta, historial=None):
    modelo, chunks, vectores = preparar_buscador()

    secciones = cargar_secciones(
        CARPETA_RAG / "contexto_lucIA.md"
    )

    return responder(
        pregunta=pregunta,
        chunks=chunks,
        vectores=vectores,
        modelo=modelo,
        secciones=secciones,
        nombre_banco="Banco MavericsAI",
        historial=(historial or [])[-8:],
        modelo_llm="qwen2.5:3b",
    )