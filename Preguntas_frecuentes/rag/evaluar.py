import json
from pathlib import Path

from cargar import cargar_pdf
from limpiar import limpiar
from trocear import trocear
from embeddings import cargar_modelo, crear_embeddings
from indice import buscar_exacto
from embeddings import cargar_modelo
from rag import preparar_indice

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
 
 
 RESULTADOS CON UN INDICE DE DOS Y 1 DE 1 
 k= 1 | 57 de 86 | 66.3%
k= 2 | 70 de 86 | 81.4%
k= 3 | 77 de 86 | 89.5%
k= 4 | 79 de 86 | 91.9%
k= 5 | 81 de 86 | 94.2%
k= 6 | 82 de 86 | 95.3%
k= 7 | 84 de 86 | 97.7%
k= 8 | 84 de 86 | 97.7%
k= 9 | 84 de 86 | 97.7%
k=10 | 84 de 86 | 97.7%
 """

#Busqueda densa, mejorar con la hibrida
def cargar_preguntas(ruta):
    """cargo las prguntas"""
    preguntas = []
    caso = None
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            caso = json.loads(linea)
            preguntas.append((caso["question"], caso["expected_article_ids"]))
    return preguntas


def recall_por_k(chunks, vectores, modelo, k_maximo=10,ruta_preguntas="../evaluacion/casos_desarrollo.jsonl"):
    vectores_preguntas = []
    recalls = []
    ids_encontrados = []
    preguntas = []
    # 1. Convertir cada pregunta en vector
    preguntas =cargar_preguntas(ruta_preguntas)
    for pregunta  in preguntas:
        v = modelo.encode(["query: " + pregunta[0]], normalize_embeddings=True)[0]
        vectores_preguntas.append(v)

    # 2. Para cada k, recorrer las preguntas y contar cuántas aciertan
    for k in range(1, k_maximo + 1):
        aciertos = 0
        for i in range(len(preguntas)):
            esperado = preguntas[i][1][0] #pillo la pregunta, la segunda tupla con los id y como alguno tiene 2 cojo el texto de la primera posicion
            resultados = buscar_exacto(vectores_preguntas[i], vectores, k)
            for resultado in resultados:
                ids_encontrados.append(chunks[resultado[1]].id)
            if esperado in ids_encontrados:
                aciertos += 1

        recalls.append(aciertos / len(preguntas))    # el Recall de este k
        print(f"k={k:2} | {aciertos} de {len(preguntas)} | {recalls[-1]:.1%}")

    return recalls


def main():
    nombre_modelo = "intfloat/multilingual-e5-small"
    modelo = cargar_modelo(nombre_modelo)
    chunks, vectores = preparar_indice("../datos", "../indice", modelo, nombre_modelo)
    print(len(chunks), "chunks |", vectores.shape)

    recall_por_k(chunks, vectores, modelo)


if __name__ == "__main__":
    main()