"""
Revisa los CSV de data/ en busca de problemas típicos. Ejecútalo cada vez que añadas frases.

Uso (desde la carpeta raíz del proyecto):
    python src/revisar_datos.py

Qué comprueba:
  1. Cuántas frases hay de cada clase en cada conjunto.
  2. Frases repetidas, dentro de un conjunto o entre conjuntos.
  3. Frases de train/val casi iguales a alguna del test (harían el test "tramposo").
  4. Palabras que aparecen casi solo en una clase. Que "hipoteca" o "tarjeta" salgan aquí
     es normal: son el tema. Lo peligroso son palabras de ESTILO ("che", "oiga", "buenas")
     o palabras que pueden salir en ambas clases ("casa", "piso", "cuota"): el modelo
     aprende el atajo "si sale esta palabra, es tal clase" en vez de entender la frase.
"""
import re
import unicodedata
from collections import Counter
from itertools import product

import pandas as pd

import config_hipotecas as config

UMBRAL_PARECIDO = 0.75   # proporción de palabras compartidas para considerar dos frases "casi iguales"
MIN_APARICIONES = 8      # solo se analizan palabras que salen al menos estas veces en train


def palabras(texto: str) -> list[str]:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))   # quita tildes
    return re.findall(r"[a-zñ0-9]+", texto)


def parecido(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def main():
    datos = {c: pd.read_csv(config.DATOS / f"{c}.csv") for c in ("train", "val", "test")}

    print("1. TAMAÑO Y CLASES")
    for nombre, df in datos.items():
        n1 = int(df.label.sum())
        print(f"   {nombre:<5} {len(df):>5} frases | hipoteca {n1:>4} ({n1 / len(df):.0%}) "
              f"| otro {len(df) - n1:>4}")

    print("\n2. FRASES REPETIDAS")
    vistas, hay = {}, False
    for nombre, df in datos.items():
        for texto in df.text:
            clave = " ".join(palabras(texto))
            if clave in vistas:
                print(f"   [{vistas[clave]} y {nombre}] {texto}")
                hay = True
            vistas.setdefault(clave, nombre)
    if not hay:
        print("   ninguna")

    print(f"\n3. FRASES DE TRAIN/VAL CASI IGUALES A ALGUNA DEL TEST (>= {UMBRAL_PARECIDO:.0%})")
    test = [(t, set(palabras(t))) for t in datos["test"].text]
    hay = False
    for nombre in ("train", "val"):
        for texto, (texto_test, p_test) in product(datos[nombre].text, test):
            if parecido(set(palabras(texto)), p_test) >= UMBRAL_PARECIDO:
                print(f"   [{nombre}] {texto}\n   [test ] {texto_test}\n")
                hay = True
    if not hay:
        print("   ninguna")

    print(f"\n4. PALABRAS QUE EN TRAIN SALEN CASI SOLO EN UNA CLASE (>= {MIN_APARICIONES} veces)")
    train = datos["train"]
    cuenta = {0: Counter(), 1: Counter()}
    for texto, label in zip(train.text, train.label):
        cuenta[label].update(set(palabras(texto)))
    proporcion_base = train.label.mean()
    filas = []
    for w in set(cuenta[0]) | set(cuenta[1]):
        n0, n1 = cuenta[0][w], cuenta[1][w]
        if n0 + n1 >= MIN_APARICIONES and len(w) > 2:
            filas.append((n1 / (n0 + n1), w, n1, n0))
    print(f"   (en todo train, el {proporcion_base:.0%} de las frases son de hipoteca)")
    print("   Casi solo en HIPOTECA:")
    for frac, w, n1, n0 in sorted(filas, reverse=True)[:30]:
        if frac >= 0.9:
            print(f"     {w:<16} hipoteca {n1:>3} | otro {n0:>3}")
    print("   Casi solo en OTRO:")
    for frac, w, n1, n0 in sorted(filas)[:30]:
        if frac <= 0.1:
            print(f"     {w:<16} hipoteca {n1:>3} | otro {n0:>3}")


if __name__ == "__main__":
    main()
