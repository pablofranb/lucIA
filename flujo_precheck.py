import unicodedata

from flujo_hipoteca import leer_numero
from precheck_hipoteca import (
    NUMERICAS,
    preparar_precheck,
    evaluar_precheck,
)


CAMPOS = [
    "age",
    "income",
    "numcards",
    "storecar",
    "loans",
    "numkids",
    "marital",
    "mortgage",
    "howpaid",
]

PREGUNTAS = [
    "¿Qué edad tiene el solicitante?",
    "¿Cuáles son sus ingresos anuales?",
    "¿Cuántas tarjetas bancarias tiene?",
    "¿Cuántas tarjetas de tiendas tiene?",
    "¿Cuántos préstamos tiene actualmente?",
    "¿Cuántos hijos tiene?",
    (
        "¿Cuál es su estado civil? Escribe: soltero, casado "
        "o divorciado/separado/viudo."
    ),
    "¿Tiene ya una hipoteca? Responde sí o no.",
    "¿Recibe sus ingresos semanalmente o mensualmente?",
]

OPCIONES = {
    "marital": {
        "s": "s",
        "soltero": "s",
        "soltera": "s",
        "m": "m",
        "casado": "m",
        "casada": "m",
        "dsw": "dsw",
        "divorciado": "dsw",
        "divorciada": "dsw",
        "separado": "dsw",
        "separada": "dsw",
        "viudo": "dsw",
        "viuda": "dsw",
        "divorciado/separado/viudo": "dsw",
    },
    "mortgage": {
        "si": "y",
        "y": "y",
        "no": "n",
        "n": "n",
    },
    "howpaid": {
        "semanal": "w",
        "semanalmente": "w",
        "w": "w",
        "mensual": "m",
        "mensualmente": "m",
        "m": "m",
    },
}


def normalizar(texto):
    texto = texto.strip().lower().rstrip(".!")
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )


def iniciar_precheck():
    estado = {"paso": 0, "datos": {}}

    respuesta = (
        "Vamos a probar la comprobación orientativa del proyecto "
        "con un caso ficticio. No aprueba ni deniega una hipoteca.\n\n"
        "Te pediré los datos uno a uno. Puedes escribir "
        "«cancelar» para salir.\n\n"
        + PREGUNTAS[0]
    )

    return respuesta, estado


def continuar_precheck(texto, estado):
    if normalizar(texto) in {"cancelar", "salir"}:
        return (
            "Comprobación cancelada. ¿En qué más puedo ayudarte?",
            None,
        )

    paso = estado["paso"]
    campo = CAMPOS[paso]
    datos = dict(estado["datos"])

    try:
        _, rangos, categorias_validas = preparar_precheck()

        if campo in NUMERICAS:
            valor = leer_numero(texto)

            if campo != "income" and not valor.is_integer():
                raise ValueError("Introduce un número entero.")

            minimo = float(rangos.loc["min", campo])
            maximo = float(rangos.loc["max", campo])

            if not minimo <= valor <= maximo:
                raise ValueError(
                    "El modelo de prueba solo cubre valores "
                    f"entre {minimo:g} y {maximo:g} para este dato. "
                    "No cambies un dato real para encajarlo: "
                    "puedes cancelar la comprobación."
                )

            if campo != "income":
                valor = int(valor)

        else:
            valor = OPCIONES[campo].get(normalizar(texto))

            if valor is None:
                raise ValueError(
                    "No he entendido la respuesta. "
                    "Utiliza una de las opciones de la pregunta."
                )

            if valor not in categorias_validas[campo]:
                raise ValueError(
                    "Esa opción no está cubierta por los datos del modelo."
                )

        datos[campo] = valor

        if paso < len(CAMPOS) - 1:
            nuevo_estado = {
                "paso": paso + 1,
                "datos": datos,
            }
            return PREGUNTAS[paso + 1], nuevo_estado

        resultado = evaluar_precheck(datos)
        respuesta = resultado["mensaje"]

        if resultado["probabilidad"] is not None:
            respuesta += (
                "\n\nProbabilidad estimada por el modelo para la "
                "etiqueta «buen riesgo»: "
                f"{resultado['probabilidad']:.1%}. "
                "No es la probabilidad de aprobación de una hipoteca."
            )

        respuesta += (
            "\n\nPuedes hacer una simulación de cuota escribiendo "
            "«Quiero simular una hipoteca»."
        )

        return respuesta, None

    except (ValueError, TypeError, OverflowError) as error:
        return f"{error}\n\n{PREGUNTAS[paso]}", estado