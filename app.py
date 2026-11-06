import re
import unicodedata

import streamlit as st

from conexion_clasificador import clasificar_mensaje
from conexion_rag import responder_consulta
from detector_operacion import detectar_operacion
from flujo_hipoteca import iniciar_hipoteca, continuar_hipoteca
from flujo_precheck import iniciar_precheck, continuar_precheck


def normalizar(texto):
    texto = texto.strip().lower().strip("¿?¡!. ")
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )


COMANDOS_SIMULACION = {
    "/simular",
    "simular hipoteca",
    "calcular hipoteca",
    "quiero simular una hipoteca",
    "quiero calcular una hipoteca",
}

COMANDOS_PRECHECK = {
    "/precheck",
    "precheck",
    "pre-check",
    "comprobar elegibilidad",
    "quiero comprobar mi elegibilidad",
    "quiero hacer el precheck",
}


def iniciar_conversacion():
    st.session_state.mensajes = []
    st.session_state.estado_hipoteca = None
    st.session_state.estado_precheck = None
    st.session_state.consulta_pendiente = None
    st.session_state.departamento_activo = None


def mostrar_mensaje(mensaje):
    with st.chat_message(mensaje["role"]):
        st.write(mensaje["content"])

        if mensaje.get("fuentes"):
            with st.expander("Ver documentos consultados"):
                for fuente in mensaje["fuentes"]:
                    st.write(fuente)


def listar_fuentes(encontrados):
    return list(dict.fromkeys(
        f"{fragmento.documento} — página {fragmento.pagina}"
        for fragmento, similitud in encontrados
    ))


def es_seguimiento(texto):
    texto = normalizar(texto)

    temas = (
        "hipoteca",
        "tarjeta",
        "cuenta",
        "transferencia",
        "bizum",
        "cajero",
        "prestamo",
        "fraude",
    )

    if any(tema in texto for tema in temas):
        return False

    return texto.startswith((
        "y ",
        "entonces ",
        "eso ",
        "esa ",
        "ese ",
        "me lo ",
        "explicamelo",
        "puedes explicarlo",
    ))


def es_respuesta_de_datos(texto):
    orden = normalizar(texto)

    opciones = {
        "si", "no", "s", "m", "n", "y", "w", "dsw",
        "soltero", "soltera",
        "casado", "casada",
        "divorciado", "divorciada",
        "separado", "separada",
        "viudo", "viuda",
        "divorciado/separado/viudo",
        "semanal", "semanalmente",
        "mensual", "mensualmente",
    }

    if orden in opciones:
        return True

    # Respuestas directas como 35, 250.000 €, 3,5 % o 30 años.
    return bool(re.fullmatch(
        r"(?:tengo\s+|son\s+|a\s+)?"
        r"-?\d[\d., ]*"
        r"\s*(?:€|euros?|%|anos?)?",
        orden,
    ))


def responder_departamento(texto, historial, departamento):
    orden = normalizar(texto)

    if departamento == "Hipotecas":
        if orden in COMANDOS_PRECHECK:
            respuesta, estado = iniciar_precheck()
            st.session_state.estado_precheck = estado
            return respuesta, [], True

        if orden in COMANDOS_SIMULACION:
            respuesta, estado = iniciar_hipoteca()
            st.session_state.estado_hipoteca = estado
            return respuesta, [], True

    if departamento in {"Hipotecas", "Atención al cliente"}:
        with st.spinner("LucIA está preparando la respuesta…"):
            respuesta, encontrados = responder_consulta(
                texto,
                historial,
            )

        return respuesta, listar_fuentes(encontrados), False

    raise ValueError("Departamento desconocido.")


st.title("LucIA")
st.caption("Asistente virtual de Banco MavericsAI")

if "mensajes" not in st.session_state:
    iniciar_conversacion()

for clave in (
    "estado_hipoteca",
    "estado_precheck",
    "consulta_pendiente",
    "departamento_activo",
):
    if clave not in st.session_state:
        st.session_state[clave] = None

MODOS = [
    "Automático",
    "Atención al cliente",
    "Hipotecas",
]

if st.session_state.get("modo") not in MODOS:
    st.session_state.modo = "Automático"

with st.sidebar:
    st.header("Pruebas del proyecto")

    modo = st.selectbox(
        "Modo de atención",
        MODOS,
        key="modo",
        on_change=iniciar_conversacion,
    )

    if modo == "Automático":
        st.caption("El clasificador elige el departamento.")
    else:
        st.caption("Selección manual para probar esta rama.")

    st.info(
        "Puedes pedir una simulación o un precheck "
        "con tus propias palabras.\n\n"
        "Ejemplos:\n"
        "«Simúlame una hipoteca».\n"
        "«¿Soy elegible para una hipoteca?».\n\n"
        "También puedes pedir cambiar de operación "
        "durante el proceso.\n\n"
        "Para salir, escribe «cancelar»."
    )

    st.button(
        "Nueva conversación",
        on_click=iniciar_conversacion,
    )

if not st.session_state.mensajes:
    with st.chat_message("assistant"):
        st.write(
            "Hola, soy LucIA, la asistente virtual "
            "de Banco MavericsAI. ¿En qué puedo ayudarte?"
        )

for mensaje in st.session_state.mensajes:
    mostrar_mensaje(mensaje)

texto = st.chat_input("Escribe tu mensaje…")

if texto and texto.strip():
    texto = texto.strip()
    orden = normalizar(texto)

    # Estos mensajes no se incluyen en el historial de Ollama.
    historial = [
        {
            "role": mensaje["role"],
            "content": mensaje["content"],
        }
        for mensaje in st.session_state.mensajes
        if not mensaje.get("privado", False)
    ]

    with st.chat_message("user"):
        st.write(texto)

    try:
        respuesta = None
        fuentes = []
        privado_usuario = False
        privado_respuesta = False

        proceso_activo = (
            st.session_state.estado_precheck is not None
            or st.session_state.estado_hipoteca is not None
        )

        # Durante un proceso, una petición nueva puede cambiar
        # entre simulación y elegibilidad.
        # Las respuestas numéricas y las opciones reconocidas
        # se procesan directamente, sin llamar al detector.
        if (
            proceso_activo
            and orden not in {"cancelar", "salir"}
            and not es_respuesta_de_datos(texto)
        ):
            if orden in COMANDOS_PRECHECK:
                operacion = "PRECHECK"

            elif orden in COMANDOS_SIMULACION:
                operacion = "SIMULACION"

            else:
                with st.spinner("Entendiendo qué necesitas…"):
                    operacion = detectar_operacion(texto)

            if operacion == "PRECHECK":
                respuesta, estado = iniciar_precheck()

                st.session_state.estado_hipoteca = None
                st.session_state.estado_precheck = estado
                st.session_state.consulta_pendiente = None
                st.session_state.departamento_activo = "Hipotecas"

                privado_usuario = True
                privado_respuesta = True

            elif operacion == "SIMULACION":
                respuesta, estado = iniciar_hipoteca()

                st.session_state.estado_precheck = None
                st.session_state.estado_hipoteca = estado
                st.session_state.consulta_pendiente = None
                st.session_state.departamento_activo = "Hipotecas"

                privado_usuario = True
                privado_respuesta = True

        # Si hemos iniciado otra operación, ya tenemos
        # la pregunta inicial y no interpretamos el mensaje como dato.
        if respuesta is not None:
            pass

        elif st.session_state.estado_precheck is not None:
            respuesta, estado = continuar_precheck(
                texto,
                st.session_state.estado_precheck,
            )

            st.session_state.estado_precheck = estado
            privado_usuario = True
            privado_respuesta = True

        elif st.session_state.estado_hipoteca is not None:
            respuesta, estado = continuar_hipoteca(
                texto,
                st.session_state.estado_hipoteca,
            )

            st.session_state.estado_hipoteca = estado
            privado_usuario = True
            privado_respuesta = True

        else:
            departamento = None
            consulta = texto
            historial_consulta = historial
            pendiente = st.session_state.consulta_pendiente
            resolviendo_pendiente = False

            # Fuera de un proceso, identificamos si el cliente
            # quiere iniciar una simulación o un precheck.
            if (
                pendiente is None
                and modo in {"Automático", "Hipotecas"}
                and orden not in COMANDOS_SIMULACION
                and orden not in COMANDOS_PRECHECK
            ):
                with st.spinner("Entendiendo qué necesitas…"):
                    operacion = detectar_operacion(
                        texto,
                        historial,
                    )

                if operacion == "SIMULACION":
                    consulta = "quiero simular una hipoteca"
                    orden = normalizar(consulta)

                elif operacion == "PRECHECK":
                    consulta = "quiero comprobar mi elegibilidad"
                    orden = normalizar(consulta)

            if pendiente is not None:
                privado_usuario = True

                if orden in {"cancelar", "salir"}:
                    st.session_state.consulta_pendiente = None

                    respuesta = (
                        "Consulta cancelada. "
                        "¿En qué más puedo ayudarte?"
                    )

                    privado_respuesta = True

                elif orden in {"si", "hipotecas", "hipoteca"}:
                    departamento = "Hipotecas"
                    consulta = pendiente["texto"]
                    historial_consulta = pendiente["historial"]
                    resolviendo_pendiente = True

                elif orden in {
                    "no",
                    "atencion al cliente",
                    "atencion",
                }:
                    departamento = "Atención al cliente"
                    consulta = pendiente["texto"]
                    historial_consulta = pendiente["historial"]
                    resolviendo_pendiente = True

                else:
                    respuesta = (
                        "¿La consulta anterior es sobre hipotecas? "
                        "Responde sí o no, o escribe «cancelar»."
                    )

                    privado_respuesta = True

            elif modo != "Automático":
                departamento = modo

            elif (
                orden in COMANDOS_SIMULACION
                or orden in COMANDOS_PRECHECK
            ):
                departamento = "Hipotecas"

            elif (
                st.session_state.departamento_activo is not None
                and es_seguimiento(texto)
            ):
                departamento = (
                    st.session_state.departamento_activo
                )

            else:
                with st.spinner("Identificando el departamento…"):
                    prediccion = clasificar_mensaje(texto)

                if prediccion["dudosa"]:
                    st.session_state.consulta_pendiente = {
                        "texto": texto,
                        "historial": historial,
                    }

                    respuesta = (
                        "Para atenderte mejor, ¿tu consulta "
                        "es sobre hipotecas? Responde sí o no."
                    )

                    privado_respuesta = True

                else:
                    departamento = prediccion["departamento"]

            if respuesta is None:
                respuesta, fuentes, privado_respuesta = (
                    responder_departamento(
                        consulta,
                        historial_consulta,
                        departamento,
                    )
                )

                privado_usuario = (
                    privado_usuario or privado_respuesta
                )

                st.session_state.departamento_activo = departamento

                if resolviendo_pendiente:
                    st.session_state.consulta_pendiente = None

        mensaje_usuario = {
            "role": "user",
            "content": texto,
            "privado": privado_usuario,
        }

        mensaje_asistente = {
            "role": "assistant",
            "content": respuesta,
            "fuentes": fuentes,
            "privado": privado_respuesta,
        }

        st.session_state.mensajes.extend([
            mensaje_usuario,
            mensaje_asistente,
        ])

        mostrar_mensaje(mensaje_asistente)

    except Exception as error:
        st.error(f"No se ha podido responder: {error}")
        st.caption("Puedes volver a enviar tu mensaje.")