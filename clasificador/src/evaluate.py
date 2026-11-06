"""
Evalúa el modelo entrenado sobre un conjunto de frases que no vio al entrenar.

Uso (desde la carpeta raíz del proyecto):
    python src/evaluate.py          # TEST: la nota final (no tomes decisiones con ella)
    python src/evaluate.py val      # VALIDACIÓN: además muestra una tabla de umbrales
                                    # para elegir UMBRAL en config_hipotecas.py

Muestra las métricas y guarda en results/ (<conjunto> = test o val):
  - metricas_<conjunto>.txt     resumen de métricas
  - predicciones_<conjunto>.csv todas las frases con su P(hipoteca)
  - errores_<conjunto>.csv      solo las frases en las que se ha equivocado
"""
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)

import config_hipotecas as config
from predict import ClasificadorHipotecas


def tabla_umbrales(y, p) -> str:
    """Precision/recall/F1 con distintos umbrales, para elegir UMBRAL con datos de validación."""
    filas = ["Umbral  Precision  Recall  F1     Falsas alarmas  Hipotecas perdidas"]
    for u in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        pred = (p >= u).astype(int)
        filas.append(f"{u:>5.1f}   {precision_score(y, pred, zero_division=0):>8.3f}  "
                     f"{recall_score(y, pred):>6.3f}  {f1_score(y, pred):.3f}  "
                     f"{int(((pred == 1) & (y == 0)).sum()):>14}  {int(((pred == 0) & (y == 1)).sum()):>18}")
    return "\n".join(filas)


def main():
    conjunto = sys.argv[1] if len(sys.argv) > 1 else "test"
    if conjunto not in ("test", "val"):
        sys.exit("Uso: python src/evaluate.py [test|val]")
    datos = pd.read_csv(config.DATOS / f"{conjunto}.csv")
    clf = ClasificadorHipotecas()

    p = np.array(clf.probabilidades(datos["text"].tolist()))
    y = datos["label"].to_numpy()
    pred = (p >= clf.umbral).astype(int)
    dudosas = (p > clf.franja_duda[0]) & (p < clf.franja_duda[1])

    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    lineas = [
        f"Conjunto: {conjunto} | {len(datos)} frases ({int(y.sum())} hipoteca, {int((1 - y).sum())} otro)",
        f"Umbral: {clf.umbral}",
        "",
        f"Accuracy  : {accuracy_score(y, pred):.3f}   (proporción de aciertos)",
        f"Precision : {precision_score(y, pred, zero_division=0):.3f}   "
        "(de las que dice HIPOTECA, cuántas lo son)",
        f"Recall    : {recall_score(y, pred):.3f}   (de las que son HIPOTECA, cuántas detecta)",
        f"F1        : {f1_score(y, pred):.3f}   (media entre precision y recall)",
        f"ROC-AUC   : {roc_auc_score(y, p):.3f}   (calidad de la probabilidad para ordenar, 1 = perfecto)",
        "",
        "Matriz de confusión:",
        "                 predice OTRO   predice HIPOTECA",
        f"  real OTRO        {tn:>5}          {fp:>5}",
        f"  real HIPOTECA    {fn:>5}          {tp:>5}",
        "",
        f"Dudosas (P(hipoteca) entre {clf.franja_duda[0]} y {clf.franja_duda[1]}): {int(dudosas.sum())}, "
        f"de las cuales {int((dudosas & (pred != y)).sum())} serían errores",
        f"Accuracy sin contar las dudosas: {accuracy_score(y[~dudosas], pred[~dudosas]):.3f}",
    ]
    if conjunto == "val":
        lineas += ["", "Cómo cambian los resultados con el umbral (elige UMBRAL con esta tabla):",
                   tabla_umbrales(y, p)]
    resumen = "\n".join(lineas)
    print(resumen)

    config.RESULTADOS.mkdir(exist_ok=True)
    (config.RESULTADOS / f"metricas_{conjunto}.txt").write_text(resumen, encoding="utf-8")
    todas = datos.assign(p_hipoteca=p.round(4), prediccion=pred)
    todas.to_csv(config.RESULTADOS / f"predicciones_{conjunto}.csv", index=False, encoding="utf-8-sig")
    errores = todas[todas.prediccion != todas.label].sort_values("p_hipoteca")
    errores.to_csv(config.RESULTADOS / f"errores_{conjunto}.csv", index=False, encoding="utf-8-sig")

    print(f"\nErrores: {len(errores)} de {len(datos)}")
    for r in errores.itertuples():
        real = config.ID2LABEL[r.label]
        print(f"  real={real:<8} P(hipoteca)={r.p_hipoteca:.3f} | {r.text}")
    print(f"\nResultados guardados en {config.RESULTADOS}")


if __name__ == "__main__":
    main()
