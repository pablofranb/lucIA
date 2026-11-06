from sentence_transformers import SentenceTransformer

def cargar_modelo(nombre="intfloat/multilingual-e5-small"):
    return SentenceTransformer(nombre)


def crear_embeddings(chunks, modelo):
    textos = []
    for chunk in chunks:
        texto = "passage: " + chunk.seccion + ". " + chunk.texto
        textos.append(texto)

    vectores = modelo.encode(textos, normalize_embeddings=True,
                             batch_size=32, show_progress_bar=True)
    return vectores