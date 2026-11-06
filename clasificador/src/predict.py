"""
Usar el modelo ya entrenado para clasificar frases.

Desde la terminal (carpeta raíz del proyecto):
    python src/predict.py "no me han cobrado la letra del piso" "quiero bloquear la tarjeta"
    python src/predict.py            # modo interactivo: escribe frases, Enter vacío para salir

Desde otro código Python (por ejemplo, la parte de tus compañeros):
    from predict import ClasificadorHipotecas
    clf = ClasificadorHipotecas()                 # carga el modelo (una sola vez)
    clf.predecir(["quiero amortizar parte de la hipoteca"])
    # -> [{'frase': '...', 'p_hipoteca': 0.98, 'p_otro': 0.02, 'etiqueta': 'HIPOTECA', 'dudosa': False}]

'dudosa' es True cuando P(hipoteca) cae en config.FRANJA_DUDA: el modelo no lo tiene
claro y es mejor preguntar al cliente que decidir a ciegas.
"""
import sys
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_hipotecas as config  # noqa: E402
from texto import normalizar  # noqa: E402


class ClasificadorHipotecas:
    def __init__(self, carpeta_modelo=config.CARPETA_MODELO, umbral: float = config.UMBRAL,
                 franja_duda: tuple[float, float] = config.FRANJA_DUDA):
        carpeta_modelo = Path(carpeta_modelo)
        if not carpeta_modelo.exists():
            raise FileNotFoundError(
                f"No encuentro el modelo en {carpeta_modelo}. Entrena primero con: python src/train.py")
        self.tokenizer = AutoTokenizer.from_pretrained(carpeta_modelo)
        self.modelo = AutoModelForSequenceClassification.from_pretrained(carpeta_modelo)
        self.modelo.eval()   # modo inferencia (sin dropout)
        self.umbral = umbral
        self.franja_duda = franja_duda

    @torch.no_grad()
    def probabilidades(self, frases: list[str], batch_size: int = 32) -> list[float]:
        """Devuelve P(hipoteca) para cada frase."""
        frases = [normalizar(f) for f in frases]   # la misma limpieza que al entrenar
        p_hipoteca = []
        for i in range(0, len(frases), batch_size):
            enc = self.tokenizer(frases[i:i + batch_size], padding=True, truncation=True,
                                 max_length=config.MAX_TOKENS, return_tensors="pt")
            logits = self.modelo(**enc).logits
            p = torch.softmax(logits, dim=-1)[:, 1]     # columna 1 = HIPOTECA
            p_hipoteca.extend(p.tolist())
        return p_hipoteca

    def predecir(self, frases: list[str]) -> list[dict]:
        if isinstance(frases, str):
            frases = [frases]
        resultados = []
        for frase, p in zip(frases, self.probabilidades(frases)):
            resultados.append({
                "frase": frase,
                "p_hipoteca": round(p, 4),
                "p_otro": round(1 - p, 4),
                "etiqueta": "HIPOTECA" if p >= self.umbral else "OTRO",
                "dudosa": self.franja_duda[0] < p < self.franja_duda[1],
            })
        return resultados


def imprimir(resultados):
    for r in resultados:
        aviso = " (dudosa)" if r["dudosa"] else ""
        print(f"P(hipoteca)={r['p_hipoteca']:.3f}  P(otro)={r['p_otro']:.3f}  "
              f"-> {r['etiqueta'] + aviso:<18} | {r['frase']}")


def main():
    clf = ClasificadorHipotecas()
    if len(sys.argv) > 1:
        imprimir(clf.predecir(sys.argv[1:]))
        return
    print("Escribe una frase y pulsa Enter (Enter vacío para salir).")
    while True:
        frase = input("> ").strip()
        if not frase:
            break
        imprimir(clf.predecir([frase]))


if __name__ == "__main__":
    main()
