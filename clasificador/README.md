# Clasificador de consultas: ¿hipoteca o no?

Recibe una frase de un cliente del banco y devuelve **P(hipoteca)** y **P(otro)** (que suman 1).
Por ejemplo:

```
P(hipoteca)=0.981  P(otro)=0.019  -> HIPOTECA | no me han cobrado la letra del piso
P(hipoteca)=0.004  P(otro)=0.996  -> OTRO     | quiero bloquear la tarjeta
```

(Esas cifras son ilustrativas; las tuyas saldrán al entrenar.)

El modelo es **BETO** (BERT preentrenado en español) con fine-tuning: se le añade una capa de
clasificación sobre el vector del token `[CLS]` y se entrena con frases etiquetadas.

---

## 1. Qué hay en la carpeta

```
clasificador/
├── data/
│   ├── train.csv      1529 frases para entrenar          (623 hipoteca / 906 otro)
│   ├── val.csv         284 frases para elegir el mejor modelo y el umbral (118 / 166)
│   └── test.csv        258 frases para la evaluación final (109 hipoteca / 149 otro)
├── src/
│   ├── config_hipotecas.py  rutas e hiperparámetros (épocas, learning rate, umbral...)
│   ├── texto.py       limpieza de las frases (la misma al entrenar y al predecir)
│   ├── train.py       fine-tuning de BETO  -> guarda el modelo en models/beto-hipotecas/
│   ├── evaluate.py    métricas en test o val -> guarda resultados en results/
│   ├── predict.py     usar el modelo con frases nuevas (terminal o desde código)
│   ├── baseline.py    modelo sencillo (TF-IDF) para comparar con BETO
│   └── revisar_datos.py  busca problemas en los CSV (repetidas, atajos...)
├── requirements.txt   librerías necesarias
├── .gitignore         evita subir el entorno y el modelo (pesa ~420 MB) a git
└── README.md
```

Cada CSV tiene dos columnas: `text` (la frase) y `label` (1 = hipoteca, 0 = otro).

**¿Por qué tres conjuntos?**

- **train**: las frases con las que el modelo aprende.
- **val** (validación): frases que el modelo no usa para aprender, pero que *sí* usamos nosotros para
  tomar decisiones: con qué época quedarnos, qué umbral poner, qué hiperparámetros probar…
- **test**: frases que solo se usan al final para dar la nota. Como no hemos decidido nada mirándolas,
  la nota es honesta. Si se usa el test para tomar decisiones, la nota deja de ser fiable.

Durante el entrenamiento, al final de cada época se guarda un **checkpoint** (una "foto" de los pesos
del modelo) si es el mejor hasta ese momento en val. Al terminar te quedas con el mejor, aunque no sea
el de la última época.

---

## 2. Instalación (una sola vez)

Necesitas **Python 3.10, 3.11 o 3.12**. Comprueba tu versión con `python --version`.
Abre una terminal **en la carpeta `clasificador`** (en VS Code: *Terminal → New Terminal*).

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si al activar sale un error de "ejecución de scripts deshabilitada", ejecuta una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y vuelve a activar.

### Linux / Mac / WSL

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Sin GPU NVIDIA**, puedes instalar torch en su versión solo-CPU, que ocupa mucho menos.
Ejecuta este comando **antes** de `pip install -r requirements.txt`:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

En VS Code, selecciona el entorno: `Ctrl+Shift+P` → *Python: Select Interpreter* → `.venv`.

Sabrás que el entorno está activo porque la terminal muestra `(.venv)` al principio de la línea.

---

## 3. Ejecución

Todos los comandos se lanzan **desde la carpeta raíz** del proyecto y con el entorno activado.

### Paso 1 — Entrenar

```bash
python src/train.py
```

- La primera vez descarga BETO de Hugging Face (~420 MB). Hace falta internet.
- Verás un aviso: *"Some weights ... are newly initialized"*. **Es normal**: es la capa de clasificación nueva.
- Por cada época se imprimen la pérdida y las métricas en validación. Cuando la validación mejora, se guarda el modelo en `models/beto-hipotecas/`.
- Duración aproximada: con GPU, 1–3 minutos. En CPU, entre 10 y 30 minutos según el ordenador.
  Si tienes GPU NVIDIA pero `train.py` dice `Dispositivo: cpu`, tienes instalado el torch solo-CPU:
  instala la versión con CUDA siguiendo <https://pytorch.org/get-started/locally/>.
  Si no tienes GPU, mira la sección 4 (Colab).

Para comprobar cuánto cambia el resultado por puro azar, entrena con otra semilla: `python src/train.py 7`.
Con tan pocas frases de test, diferencias de 1–2 puntos entre dos versiones pueden ser solo suerte.

### Paso 2 — Elegir el umbral (con val) y evaluar (con test)

```bash
python src/evaluate.py val     # incluye una tabla con distintos umbrales
python src/evaluate.py         # test: la nota final
```

Muestra accuracy, precision, recall, F1, ROC-AUC y la matriz de confusión, además de **las frases en las que se ha equivocado**.
Lo guarda todo en `results/`. Si quieres cambiar `UMBRAL`, elígelo mirando la tabla de **val**, nunca la del test.

Para comparar, `python src/baseline.py` entrena en segundos un modelo mucho más simple (TF-IDF +
regresión logística). Si BETO no le saca ventaja clara, la mejora hay que buscarla en los datos.

### Paso 3 — Usarlo con frases nuevas

```bash
python src/predict.py "me ha subido la cuota del piso por el euribor" "quiero un préstamo para el coche"
python src/predict.py          # modo interactivo
```

Desde otro script de Python (por ejemplo, la parte del proyecto de tus compañeros):

```python
import sys; sys.path.append("ruta/a/clasificador/src")
from predict import ClasificadorHipotecas

clf = ClasificadorHipotecas()          # carga el modelo una vez (tarda unos segundos)
clf.predecir(["quiero amortizar parte de la hipoteca"])
# [{'frase': '...', 'p_hipoteca': 0.98, 'p_otro': 0.02, 'etiqueta': 'HIPOTECA', 'dudosa': False}]
```

Después de cargar el modelo, cada frase tarda milisegundos.

`dudosa` es `True` cuando P(hipoteca) está entre 0.2 y 0.8 (configurable con `FRANJA_DUDA`). En esos
casos el modelo se equivoca mucho más a menudo, y lo recomendable es preguntar al cliente
("¿su consulta es sobre su hipoteca?") en vez de enviarlo a ciegas a un sitio u otro.

---

## 4. Alternativa sin GPU: Google Colab (gratis)

1. Entra en <https://colab.research.google.com> → *Nuevo cuaderno*.
2. *Entorno de ejecución → Cambiar tipo de entorno de ejecución → GPU (T4)*.
3. Sube el zip (icono de carpeta a la izquierda → subir) y ejecuta en una celda:

```python
!unzip -q clasificador.zip
%cd clasificador
!pip install -q -r requirements.txt
!python src/train.py
!python src/evaluate.py
!python src/predict.py "no me han pasado el recibo de la hipoteca"
```

4. Para llevarte el modelo entrenado a tu ordenador:

```python
!zip -qr modelo.zip models/beto-hipotecas
from google.colab import files; files.download("modelo.zip")
```

Descomprímelo dentro de tu carpeta del proyecto para que quede `models/beto-hipotecas/`.
A partir de ahí ya puedes usar `predict.py` en local sin volver a entrenar.

---

## 5. Cambiar cosas

Todo se configura en `src/config_hipotecas.py`:

| Parámetro | Para qué sirve |
|---|---|
| `EPOCAS`, `LEARNING_RATE`, `BATCH_SIZE` | Ajustan el entrenamiento. Si te quedas sin memoria, baja `BATCH_SIZE` a 8. |
| `UMBRAL` | A partir de qué P(hipoteca) se dice HIPOTECA. Bájalo (p. ej., 0.3) si es más grave no detectar una hipoteca que tener alguna falsa alarma. Elígelo con `python src/evaluate.py val`. |
| `FRANJA_DUDA` | Entre qué valores de P(hipoteca) la predicción se marca como dudosa. |
| `MODELO_BASE` | Permite probar otro modelo, por ejemplo `"PlanTL-GOB-ES/roberta-base-bne"`, sin cambiar nada más. |

---

## 6. Sobre los datos

- Todas las frases son **sintéticas** (el proyecto no tiene datos reales). Están escritas imitando a clientes distintos: formales, informales, con faltas, transcripciones de voz…
- Incluyen **negativos difíciles**: frases que hablan de casa, piso, cuota, Euríbor o préstamo pero **no** son de hipoteca (préstamo del coche, seguro de hogar, alquiler, ahorro…). Así el modelo no aprende que "piso" significa hipoteca.
- Más de la mitad de las frases de hipoteca **no contienen la palabra "hipoteca"** ("la letra del piso", "lo que debo de la casa").
- **El test está escrito aparte**, con estilos diferentes al entrenamiento. Además, se eliminaron del entrenamiento las frases demasiado parecidas a alguna del test, para que la evaluación no sea tramposa.
- Todas las etiquetas se revisaron con una segunda anotación a ciegas. Las frases ambiguas (por ejemplo, "reducir cuota amortizando", que no dice de qué préstamo habla) se eliminaron.
- Hay frases en **español de Latinoamérica** (voseo, "depto", "crédito hipotecario", "plata"…) **en las dos
  clases**, y negativos que nombran la hipoteca pero piden otra cosa ("no tengo hipoteca, solo quiero…").
  Un estilo o una palabra que solo aparece en una clase se convierte en un atajo: el modelo aprende
  "si sale X, es tal clase" en vez de entender la frase.
- Las frases escritas EN MAYÚSCULAS se pasan a minúsculas antes de entrar al modelo (`src/texto.py`):
  BETO distingue mayúsculas y, sin esto, no reconocía "HIPOTECA".
- **Cada vez que añadas frases**, ejecuta `python src/revisar_datos.py`: avisa de frases repetidas, de
  frases demasiado parecidas a las del test y de palabras que aparecen casi solo en una clase.
- Ten en cuenta que en el uso real las consultas de hipoteca serán probablemente una minoría (aquí son
  el ~40 %). Con menos hipotecas reales, la *precision* real será algo menor que la medida en el test.

## 7. Problemas frecuentes

| Problema | Solución |
|---|---|
| `ModuleNotFoundError: torch` | El entorno no está activado: activa `.venv` y repite `pip install -r requirements.txt`. |
| `No encuentro el modelo en .../models/beto-hipotecas` | Primero hay que ejecutar `python src/train.py`. |
| `CUDA out of memory` | Baja `BATCH_SIZE` a 8 en `config_hipotecas.py`. |
| La descarga de BETO falla | Comprueba la conexión. Algunas redes (como la de la universidad) bloquean huggingface.co: prueba en otra red. |
