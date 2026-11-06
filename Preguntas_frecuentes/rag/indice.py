import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from modelos import Chunk

"""
Mis resultados
Batches: 100%|██████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 8/8 [00:04<00:00,  1.85it/s]
 k | Recall@k
 1 |  62.8%
 2 |  75.6%
 3 |  83.7%
 4 |  84.9%
 5 |  89.5%
 6 |  89.5%
 7 |  91.9%
 8 |  91.9%
 9 |  91.9%
10 |  91.9%
 """
def buscar_exacto(v_pregunta, vectores, k=5):
    """Compara la pregunta con cada chunk y devuelve los k más parecidos.
    Devuelve una lista de (posición, similitud).
    Ya he normalizado los vectores por lo que para calcular el angulo se hace solo con es producto escalar"""
    similitudes = []

    for posicion in range(len(vectores)):
        similitud = np.dot(vectores[posicion], v_pregunta) 
        similitudes.append((similitud, posicion)) 

    similitudes.sort(reverse=True)                     
    return similitudes[:k]


def guardar_indice(carpeta, chunks, vectores, nombre_modelo):
    """Guarda el índice en disco para no tener que recalcularlo cada vez.

    1. Crea la carpeta (si no existe).
    2. Guarda en ella los vectores tal cual, en vectores.npy (ya vienen como una matriz).
    3. Guarda los chunks en chunks.json. Como JSON no sabe guardar objetos Chunk, uso una
       lista auxiliar donde voy metiendo cada chunk convertido a diccionario, sin modificar
       los chunks originales.
    4. Esa lista va dentro de un diccionario 'datos', junto con el nombre del modelo con el
       que se calcularon los vectores, y se vuelca en el JSON.
    """
    lista_chunks = []
    
    carpeta = Path(carpeta)
    carpeta.mkdir(exist_ok=True)                 
    np.save(carpeta / "vectores.npy", vectores)
    for chunk in chunks:
        lista_chunks.append(asdict(chunk))
    datos = {"modelo": nombre_modelo, "chunks": lista_chunks}
    with open(carpeta / "chunks.json", "w", encoding="utf-8") as f:
        json.dump(datos, f)


def cargar_indice(carpeta, nombre_modelo):
    """Carga los vectores y los chunks guardados. Comprueba que son del mismo modelo."""
    chunks = []

    carpeta = Path(carpeta)
    with open(carpeta / "chunks.json", encoding="utf-8") as f:
        datos = json.load(f)
    if datos["modelo"] != nombre_modelo:
        raise ValueError(f"El índice se creó con {datos['modelo']}, no con {nombre_modelo}")
    for diccionario in datos["chunks"]:
        chunks.append(Chunk(**diccionario))
    vectores = np.load(carpeta / "vectores.npy")
    return chunks, vectores