from dataclasses import dataclass
import pymupdf
from pathlib import Path
from modelos import Linea

def obtener_bloques(pagina):
    """Devuelve la lista de párrafos de una página."""
    contenido = pagina.get_text("dict")
    return contenido["blocks"]

def obtener_lineas(bloque):
     """Devuelve las líneas de un bloque."""
     if "lines" in bloque:
        return bloque["lines"]
     return []


def texto_de_linea(linea):
    """Junta el texto de todos los spans de la línea."""
    texto = ""
    for span in linea["spans"]:
        texto = texto + span["text"]
    return texto.strip()   

def es_negrita(span):
    """Mira si un span está en negrita (por el nombre de la fuente o por su flag)."""
    if "Bold" in span["font"]:
        return True
    return False

def cargar_pdf(ruta: str)->list[Linea]:
    doc = pymupdf.open(ruta)
    lineas = []
    for pagina in doc:
        numero_pagina = pagina.number + 1
        numero_bloque = 0
        for bloque in obtener_bloques(pagina):
            for linea in obtener_lineas(bloque):
                texto = texto_de_linea(linea)
                if texto =="":
                    continue
                primer_span = linea["spans"][0]   
                tamano = round(primer_span["size"])
                negrita = es_negrita(primer_span)
                altura = linea["bbox"][1] 

                nueva = Linea(texto, tamano, negrita, numero_pagina, numero_bloque, altura)
                lineas.append(nueva)
            numero_bloque += 1
    return lineas
