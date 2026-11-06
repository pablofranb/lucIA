"""Configuración del proyecto: rutas e hiperparámetros en un solo sitio."""
from pathlib import Path

# --- Rutas ---
RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "data"
CARPETA_MODELO = RAIZ / "models" / "beto-hipotecas"   # aquí se guarda el modelo entrenado
RESULTADOS = RAIZ / "results"

# --- Modelo preentrenado (se descarga de Hugging Face la primera vez) ---
MODELO_BASE = "dccuchile/bert-base-spanish-wwm-cased"   # BETO

# --- Etiquetas ---
ID2LABEL = {0: "OTRO", 1: "HIPOTECA"}
LABEL2ID = {"OTRO": 0, "HIPOTECA": 1}

# --- Hiperparámetros del fine-tuning ---
MAX_TOKENS = 128        # las frases son cortas; si son más largas se recortan
BATCH_SIZE = 16
EPOCAS = 4
LEARNING_RATE = 3e-5    # típico para fine-tuning de BERT (2e-5 a 5e-5)
WARMUP = 0.1            # 10% de los pasos con learning rate creciente
WEIGHT_DECAY = 0.01
SEMILLA = 42            # se puede cambiar sin tocar este archivo: python src/train.py 7

# --- Decisión ---
UMBRAL = 0.5            # si P(hipoteca) >= UMBRAL -> HIPOTECA (elígelo con: python src/evaluate.py val)
# Si P(hipoteca) cae dentro de esta franja, la predicción se marca como "dudosa": conviene
# preguntar al cliente en vez de decidir a ciegas (por ejemplo, "¿su consulta es sobre su hipoteca?").
FRANJA_DUDA = (0.2, 0.8)
