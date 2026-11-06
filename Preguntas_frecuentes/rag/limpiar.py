from modelos import Linea

def es_ruido(linea, tam_minimo):
    """Decide si una línea es ruido (True) o contenido (False)."""
    if linea.tamano < tam_minimo:                      
        return True
    if linea.texto == "Metadatos del documento original":
        return True
    return False


def arreglar_guiones(lineas):
    """Une las palabras partidas con guion al final de línea ("transfe-" + "rencia").
    Los PDFs actuales no tienen, pero se deja por si se añaden otros."""
    resultado = []
    for linea in lineas:
        if resultado:                                       
            anterior = resultado[-1]
            if anterior.texto.endswith("-") and linea.texto[:1].islower():
                anterior.texto = anterior.texto[:-1] + linea.texto  
                continue                                    
        resultado.append(linea)
    return resultado


def limpiar(lineas, tam_minimo=9):
    lineas_limpias = []
    for linea in lineas:
        if not es_ruido(linea, tam_minimo):
            lineas_limpias.append(linea)
    lineas_limpias = arreglar_guiones(lineas_limpias)
    return lineas_limpias