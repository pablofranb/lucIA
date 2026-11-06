"""
Línea base: un clasificador sencillo (TF-IDF + regresión logística) para comparar con BETO.

Si este modelo, que solo cuenta trozos de palabras, saca casi lo mismo que BETO, BETO no
está aportando mucho. Si BETO saca bastante más, es que entiende cosas que contar palabras
no capta (paráfrasis, contexto, negaciones...). Entrena en segundos y no necesita GPU.

Uso (desde la carpeta raíz del proyecto):
    python src/baseline.py
"""
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.pipeline import make_pipeline

import config_hipotecas as config
from texto import normalizar


def main():
    train = pd.read_csv(config.DATOS / "train.csv")
    modelo = make_pipeline(
        # trozos de 2 a 5 letras: tolera faltas de ortografía y palabras sin tilde
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), lowercase=True, sublinear_tf=True),
        LogisticRegression(C=10, max_iter=2000),
    )
    modelo.fit(train["text"].map(normalizar), train["label"])

    for conjunto in ("val", "test"):
        datos = pd.read_csv(config.DATOS / f"{conjunto}.csv")
        p = modelo.predict_proba(datos["text"].map(normalizar))[:, 1]
        pred = (p >= 0.5).astype(int)
        print(f"{conjunto:<5} accuracy={accuracy_score(datos['label'], pred):.3f}  "
              f"F1={f1_score(datos['label'], pred):.3f}  "
              f"ROC-AUC={roc_auc_score(datos['label'], p):.3f}")


if __name__ == "__main__":
    main()
