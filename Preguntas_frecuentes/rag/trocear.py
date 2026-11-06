from dataclasses import dataclass
from modelos import Linea, Chunk

def unir_lineas(lineas):
    """Junta las líneas de un artículo en un solo texto, separadas por espacios."""
    textos = []
    for linea in lineas:
        textos.append(linea.texto)
    return " ".join(textos)

def trocear(lineas, documento, tam_titulo_pdf=20, tam_articulo=12):
    """Trocea las líneas de UN PDF: un Chunk por artículo."""
    titulo = []         # renglones del título del PDF
    seccion = ""        # título completo del PDF
    articulos = []      # lista de artículos; cada artículo es una lista de líneas
    chunks = []         # resultado final
    id_chunk = ""
    texto = ""

    # 1. La sección es el título del PDF (puede ocupar varios renglones)
    for linea in lineas:
        if linea.tamano == tam_titulo_pdf:
            titulo.append(linea.texto)
    seccion = " ".join(titulo)

    # 2. Agrupar las líneas por artículo
    for linea in lineas:
        if linea.tamano == tam_articulo:
            articulos.append([linea])          # empieza un artículo nuevo
        elif articulos:
            articulos[-1].append(linea)        # se añade al último artículo

    # 3. Convertir cada artículo en un Chunk
    for articulo in articulos:
        id_chunk = articulo[0].texto.split(" · ")[0]
        texto = unir_lineas(articulo)
        chunks.append(Chunk(
            id=id_chunk,
            texto=texto,
            seccion=seccion,
            documento=documento,
            pagina=articulo[0].pagina,
        ))

    return chunks