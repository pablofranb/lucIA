"""
rag.py — Programa principal del RAG de preguntas frecuentes.

Une las piezas (cargar, limpiar, trocear, embeddings, índice) en el orden correcto.
Es lo que importan evaluar.py, el router y la app de Streamlit.
"""
import re
from pathlib import Path

from cargar import cargar_pdf
from limpiar import limpiar
from trocear import trocear
from embeddings import crear_embeddings
from indice import guardar_indice, cargar_indice
from indice import buscar_exacto
import ollama


def preparar_indice(carpeta_pdfs, carpeta_indice, modelo, nombre_modelo):
    """Prepara el índice para poder buscar.

    1. Si el índice ya existe en carpeta_indice, lo carga (rápido).
    2. Si no existe, lo crea a partir de los PDFs (cargar, limpiar, trocear y
       embeddings) y lo guarda para la próxima vez.
    Devuelve los chunks y los vectores, en el mismo orden.
    """
    chunks = []
    vectores = None
    lineas = []

    if (Path(carpeta_indice) / "chunks.json").exists():
        print("Cargando índice guardado...")
        return cargar_indice(carpeta_indice, nombre_modelo)

    print("No hay índice: creándolo a partir de los PDFs...")
    for ruta in sorted(Path(carpeta_pdfs).glob("*.pdf")):
        lineas = cargar_pdf(ruta)
        lineas = limpiar(lineas)
        chunks += trocear(lineas, ruta.name)

    vectores = crear_embeddings(chunks, modelo)
    guardar_indice(carpeta_indice, chunks, vectores, nombre_modelo)
    return chunks, vectores

def recuperar(pregunta, chunks, vectores, modelo, k=5, umbral=0.82):
    """Busca los chunks más relevantes para la pregunta.

    Devuelve una lista de (chunk, similitud), de mayor a menor similitud.
    Si ni el mejor resultado llega al umbral, la pregunta está fuera de tema
    y devuelve una lista vacía (así no se llama al LLM).
    """
    encontrados = []

    v_pregunta = modelo.encode(["query: " + pregunta], normalize_embeddings=True)[0]
    resultados = buscar_exacto(v_pregunta, vectores, k)
    mejor_similitud = resultados[0][0]
    if mejor_similitud < umbral:
        return []


    for similitud, posicion in resultados:
        encontrados.append((chunks[posicion], similitud))
    return encontrados

def construir_mensaje(pregunta, encontrados):
    """Construye el mensaje para el LLM: los chunks recuperados como contexto + la pregunta.

    Cada chunk va con su fuente (id, sección y página) para que el LLM pueda citarla.
    """
    bloques = []
    for chunk, similitud in encontrados:
        bloques.append(f"[{chunk.id} · {chunk.seccion}, pág. {chunk.pagina}]\n{chunk.texto}")

    contexto = "\n\n".join(bloques)
    return f"<contexto>\n{contexto}\n</contexto>\n\n<pregunta>\n{pregunta}\n</pregunta>"

def generar(system, mensaje, historial=None, modelo_llm="qwen2.5:7b"):
    """Envía el prompt al LLM local (Ollama) y devuelve la respuesta en texto.

    historial: lista opcional de mensajes previos ({"role": "user"/"assistant", "content": ...}),
    de más antiguo a más reciente, para que el modelo recuerde la conversación.
    """
    mensajes = [{"role": "system", "content": system}]
    if historial:
        mensajes += historial
    mensajes.append({"role": "user", "content": mensaje})

    try:
        respuesta = ollama.chat(
            model=modelo_llm,
            messages=mensajes,
            options={"temperature": 0},
        )
        return respuesta["message"]["content"]
    except Exception as error:
        print("Error con Ollama:", error)
        return "Ahora mismo no puedo responder. Inténtalo de nuevo en unos minutos."


def cargar_secciones(ruta_contexto="contexto_lucIA.md"):
    """Lee contexto_lucIA.md y devuelve un diccionario {NOMBRE_SECCION: texto}.

    Reglas del propio fichero: cada sección empieza con una línea '=== NOMBRE ==='
    y termina donde empieza la siguiente; las líneas que empiezan por '//' son
    comentarios (se descartan); lo anterior a la primera sección se ignora.
    """
    texto = Path(ruta_contexto).read_text(encoding="utf-8")
    secciones = {}
    nombre_actual = None
    lineas_actuales = []

    for linea in texto.splitlines():
        cabecera = re.match(r"^=== (.+) ===$", linea.strip())
        if cabecera:
            if nombre_actual is not None:
                secciones[nombre_actual] = "\n".join(lineas_actuales).strip()
            nombre_actual = cabecera.group(1)
            lineas_actuales = []
            continue
        if nombre_actual is not None and not linea.strip().startswith("//"):
            lineas_actuales.append(linea)

    if nombre_actual is not None:
        secciones[nombre_actual] = "\n".join(lineas_actuales).strip()
    return secciones


def construir_system(secciones, nombre_banco="Maverics", nombre_bot="LucIA"):
    """Arma el mensaje de sistema a partir de MARCO + REGLA_DATOS_RAG (modo RAG),
    sustituyendo los <<...>> que no dependen de config.py (no hay modo voz ni
    datos extra del banco en este script de pruebas)."""
    texto = secciones["MARCO"]
    texto = texto.replace("<<REGLA_DATOS>>", secciones["REGLA_DATOS_RAG"])
    texto = texto.replace("<<REGLA_VOZ>>", "")
    texto = texto.replace("<<DATOS_BANCO>>", "")
    texto = texto.replace("<<NOMBRE_BOT>>", nombre_bot)
    texto = texto.replace("<<NOMBRE_BANCO>>", nombre_banco)
    return texto


def responder(pregunta, chunks, vectores, modelo, secciones, nombre_banco="Maverics",
              historial=None, k=5, umbral=0.82, modelo_llm="qwen2.5:7b"):
    """Responde una pregunta de principio a fin: recupera documentación y, si hay
    suficiente, llama al LLM. Si ningún fragmento supera el umbral, devuelve el
    texto fijo RESPUESTA_SIN_DOCUMENTACION sin llamar al modelo.

    historial: turnos anteriores de la conversación (ver generar()); recuperar()
    no los usa, solo busca con el texto literal de la pregunta actual.

    Devuelve (respuesta, encontrados), igual que recuperar() en su segundo valor.
    """
    encontrados = recuperar(pregunta, chunks, vectores, modelo, k, umbral)
    if not encontrados:
        respuesta = secciones["RESPUESTA_SIN_DOCUMENTACION"].replace("<<NOMBRE_BANCO>>", nombre_banco)
        return respuesta, encontrados

    system = construir_system(secciones, nombre_banco)
    mensaje = construir_mensaje(pregunta, encontrados)
    respuesta = generar(system, mensaje, historial, modelo_llm)
    return respuesta, encontrados