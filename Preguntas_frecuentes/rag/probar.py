"""
probar.py — Chatear con el RAG desde la terminal para ver respuestas reales.
"""
from embeddings import cargar_modelo
from rag import preparar_indice, responder, cargar_secciones

MAX_INTERCAMBIOS = 4


def main():
    nombre_modelo = "intfloat/multilingual-e5-small"
    modelo = cargar_modelo(nombre_modelo)
    chunks, vectores = preparar_indice("../datos", "../indice", modelo, nombre_modelo)
    secciones = cargar_secciones("contexto_lucIA.md")
    historial = []

    while True:
        pregunta = input("\nTú: ").strip()
        if pregunta == "":
            break

        respuesta, encontrados = responder(pregunta, chunks, vectores, modelo, secciones,
                                            historial=historial)

        historial.append({"role": "user", "content": pregunta})
        historial.append({"role": "assistant", "content": respuesta})
        historial = historial[-MAX_INTERCAMBIOS * 2:]

        print("\nAsistente:", respuesta)
        for chunk, similitud in encontrados:
            print(f"   · {similitud:.3f} | {chunk.id} | {chunk.seccion}")


if __name__ == "__main__":
    main()