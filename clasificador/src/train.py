"""
Fine-tuning de BETO para clasificar frases en HIPOTECA / OTRO.

Qué hace:
  1. Carga data/train.csv y data/val.csv.
  2. Carga BETO preentrenado y le añade una capa de clasificación nueva (2 salidas)
     sobre el vector del token [CLS].
  3. Entrena: para cada lote -> forward -> cross-entropy con la etiqueta -> backprop
     -> actualizar pesos (los de la capa nueva y, un poco, los de BETO).
  4. Al final de cada época evalúa en validación y guarda el modelo si es el mejor
     hasta ahora (menor pérdida en validación).

Uso (desde la carpeta raíz del proyecto):
    python src/train.py          # semilla de config_hipotecas.py
    python src/train.py 7        # otra semilla (para ver cuánto varía el resultado por azar)
"""
import random
import sys
import time

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          get_linear_schedule_with_warmup)

import config_hipotecas as config
from texto import normalizar


def fijar_semilla(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def elegir_dispositivo() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")          # GPU NVIDIA
    if torch.backends.mps.is_available():
        return torch.device("mps")           # GPU de Mac (Apple Silicon)
    return torch.device("cpu")


def crear_dataloader(df: pd.DataFrame, tokenizer, mezclar: bool) -> DataLoader:
    ejemplos = list(zip(df["text"].map(normalizar).tolist(), df["label"].tolist()))

    def collate(lote):
        textos, etiquetas = zip(*lote)
        # tokeniza el lote: añade [CLS]/[SEP], rellena (padding) hasta la frase más larga
        enc = tokenizer(list(textos), padding=True, truncation=True,
                        max_length=config.MAX_TOKENS, return_tensors="pt")
        enc["labels"] = torch.tensor(etiquetas, dtype=torch.long)
        return enc

    return DataLoader(ejemplos, batch_size=config.BATCH_SIZE, shuffle=mezclar,
                      collate_fn=collate)


@torch.no_grad()
def evaluar(modelo, loader, dispositivo) -> dict:
    modelo.eval()
    perdida_total, aciertos, n = 0.0, 0, 0
    tp = fp = fn = 0
    for lote in loader:
        lote = {k: v.to(dispositivo) for k, v in lote.items()}
        salida = modelo(**lote)               # si pasamos labels, devuelve también la loss
        pred = salida.logits.argmax(dim=-1)
        y = lote["labels"]
        perdida_total += salida.loss.item() * len(y)
        aciertos += (pred == y).sum().item()
        tp += ((pred == 1) & (y == 1)).sum().item()
        fp += ((pred == 1) & (y == 0)).sum().item()
        fn += ((pred == 0) & (y == 1)).sum().item()
        n += len(y)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"loss": perdida_total / n, "accuracy": aciertos / n, "f1": f1}


def main():
    semilla = int(sys.argv[1]) if len(sys.argv) > 1 else config.SEMILLA
    fijar_semilla(semilla)
    dispositivo = elegir_dispositivo()
    print(f"Dispositivo: {dispositivo} | Semilla: {semilla}")

    train_df = pd.read_csv(config.DATOS / "train.csv")
    val_df = pd.read_csv(config.DATOS / "val.csv")
    print(f"Train: {len(train_df)} frases | Val: {len(val_df)} frases")

    # BETO + capa de clasificación nueva (num_labels=2). El aviso de que algunos pesos
    # "are newly initialized" es normal: es justo esa capa nueva.
    tokenizer = AutoTokenizer.from_pretrained(config.MODELO_BASE)
    modelo = AutoModelForSequenceClassification.from_pretrained(
        config.MODELO_BASE, num_labels=2,
        id2label=config.ID2LABEL, label2id=config.LABEL2ID,
    ).to(dispositivo)

    train_loader = crear_dataloader(train_df, tokenizer, mezclar=True)
    val_loader = crear_dataloader(val_df, tokenizer, mezclar=False)

    optimizador = torch.optim.AdamW(modelo.parameters(), lr=config.LEARNING_RATE,
                                    weight_decay=config.WEIGHT_DECAY)
    pasos_totales = len(train_loader) * config.EPOCAS
    scheduler = get_linear_schedule_with_warmup(
        optimizador, num_warmup_steps=int(config.WARMUP * pasos_totales),
        num_training_steps=pasos_totales)

    mejor_loss = float("inf")
    for epoca in range(1, config.EPOCAS + 1):
        modelo.train()
        inicio, perdida_acum = time.time(), 0.0
        for paso, lote in enumerate(train_loader, start=1):
            lote = {k: v.to(dispositivo) for k, v in lote.items()}
            salida = modelo(**lote)            # forward + cross-entropy
            salida.loss.backward()             # backpropagation
            torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
            optimizador.step()                 # actualizar pesos
            scheduler.step()
            optimizador.zero_grad()
            perdida_acum += salida.loss.item()
            if paso % 20 == 0 or paso == len(train_loader):
                print(f"  época {epoca} | paso {paso}/{len(train_loader)} "
                      f"| loss media {perdida_acum / paso:.4f}", flush=True)

        m = evaluar(modelo, val_loader, dispositivo)
        print(f"Época {epoca}: val_loss={m['loss']:.4f}  val_accuracy={m['accuracy']:.3f}  "
              f"val_f1={m['f1']:.3f}  ({time.time() - inicio:.0f}s)")

        if m["loss"] < mejor_loss:
            mejor_loss = m["loss"]
            config.CARPETA_MODELO.mkdir(parents=True, exist_ok=True)
            modelo.save_pretrained(config.CARPETA_MODELO)
            tokenizer.save_pretrained(config.CARPETA_MODELO)
            print(f"  -> mejor modelo hasta ahora, guardado en {config.CARPETA_MODELO}")

    print("\nEntrenamiento terminado. Siguiente paso: python src/evaluate.py")


if __name__ == "__main__":
    main()
