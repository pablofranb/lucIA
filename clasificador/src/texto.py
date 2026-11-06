"""Limpieza de las frases antes de pasarlas al modelo (igual al entrenar y al predecir)."""


def normalizar(texto: str) -> str:
    """Quita espacios sobrantes y pasa a minúsculas las frases escritas EN MAYÚSCULAS.

    BETO distingue mayúsculas y minúsculas: "HIPOTECA" lo parte en trozos raros que no
    se parecen a "hipoteca", y el modelo deja de reconocerla. Como casi nadie escribe
    todo en mayúsculas salvo para "gritar", esas frases se pasan a minúsculas.
    Las siglas sueltas dentro de una frase normal (ITP, TPV, IBAN...) no se tocan.
    """
    texto = " ".join(str(texto).split())
    mayusculas = sum(c.isupper() for c in texto)
    minusculas = sum(c.islower() for c in texto)
    if mayusculas > minusculas:
        texto = texto.lower()
    return texto
