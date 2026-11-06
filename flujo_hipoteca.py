import math
import re

from calculadora_hipoteca import calcular_hipoteca


PREGUNTAS = [
    "¿Cuál es el precio de la vivienda en euros?",
    "¿Cuánto aportarías de entrada, en euros?",
    (
        "¿Qué tipo de interés anual quieres usar para la simulación? "
        "Por ejemplo, escribe 3,5 para un 3,5 %. "
        "Es un dato de prueba, no una oferta del banco."
    ),
    "¿A cuántos años quieres simular la hipoteca?",
]

CAMPOS = [
    "precio_vivienda",
    "entrada",
    "tipo_interes_anual",
    "años",
]


def iniciar_hipoteca():
    estado = {"paso": 0, "datos": {}}
    return (
        "Vamos a hacer una simulación orientativa. "
        "Puedes escribir «cancelar» para salir.\n\n"
        + PREGUNTAS[0],
        estado,
    )


def leer_numero(texto):
    texto = texto.replace(" ", "")
    numeros = re.findall(r"-?\d[\d.,]*", texto)

    if len(numeros) != 1:
        raise ValueError("Escribe un único número usando cifras.")

    numero = numeros[0].rstrip(".,")

    if "," in numero:
        numero = numero.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", numero):
        numero = numero.replace(".", "")

    valor = float(numero)

    if not math.isfinite(valor):
        raise ValueError("Escribe un número válido.")

    return valor


def continuar_hipoteca(texto, estado):
    if texto.strip().lower() in {"cancelar", "salir"}:
        return "Simulación cancelada. ¿En qué más puedo ayudarte?", None

    paso = estado["paso"]
    datos = dict(estado["datos"])

    try:
        valor = leer_numero(texto)

        if paso == 0 and valor <= 0:
            raise ValueError("El precio debe ser mayor que cero.")

        if paso == 1 and not 0 <= valor < datos["precio_vivienda"]:
            raise ValueError(
                "La entrada debe ser igual o mayor que cero "
                "y menor que el precio de la vivienda."
            )

        if paso == 2 and valor < 0:
            raise ValueError("El interés no puede ser negativo.")

        if paso == 3:
            if valor <= 0 or not valor.is_integer():
                raise ValueError("Escribe un número entero de años mayor que cero.")
            valor = int(valor)

        datos[CAMPOS[paso]] = valor

        if paso < 3:
            nuevo_estado = {"paso": paso + 1, "datos": datos}
            return PREGUNTAS[paso + 1], nuevo_estado

        resultado = calcular_hipoteca(**datos)

        respuesta = (
            f"La cuota mensual estimada sería de "
            f"**{resultado['cuota_mensual']:,.2f} €**.\n\n"
            f"- Importe del préstamo: "
            f"{resultado['importe_prestamo']:,.2f} €.\n"
            f"- Interés anual: {datos['tipo_interes_anual']:g} %.\n"
            f"- Plazo: {datos['años']} años.\n"
            f"- Total pagado en cuotas: "
            f"{resultado['importe_total']:,.2f} €.\n"
            f"- Intereses totales: "
            f"{resultado['intereses_totales']:,.2f} €.\n\n"
            "Es una simulación con interés fijo y cuotas mensuales constantes. "
            "No incluye impuestos, comisiones, seguros ni otros gastos, "
            "y no supone una aprobación ni una oferta del banco."
        )

        return respuesta, None

    except (ValueError, OverflowError, ZeroDivisionError) as error:
        return f"{error}\n\n{PREGUNTAS[paso]}", estado