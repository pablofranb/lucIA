# LucIA

**Autor:** Pablo

LucIA es un asistente virtual para un banco ficticio, hecho con Python y Streamlit como proyecto de clase. El cliente escribe en el chat y LucIA decide qué tipo de consulta es y la atiende de una forma u otra.

> Todos los datos, documentos y condiciones son de ejemplo. No es un banco real ni da información oficial.

## Índice

- [Qué hace](#qué-hace)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Cómo funciona el RAG](#cómo-funciona-el-rag)
- [Resultados del clasificador](#resultados-del-clasificador)
- [Cómo ejecutarlo](#cómo-ejecutarlo)
- [Limitaciones](#limitaciones)
- [Tecnologías](#tecnologías)

## Qué hace

| Función | Descripción |
|---|---|
| **Clasificador** | Un modelo BETO (BERT en español) con fine-tuning decide si el mensaje va de hipotecas o de otra cosa. Si no está seguro, le pregunta al cliente. |
| **Preguntas frecuentes (RAG)** | Busca en 34 PDFs de atención al cliente (cuentas, tarjetas, transferencias, reclamaciones...) los fragmentos más parecidos a la pregunta y se los pasa a un modelo local de Ollama (`qwen2.5:3b`) para que redacte la respuesta. Debajo se pueden ver los documentos consultados. |
| **Simulador de hipoteca** | Pregunta precio de la vivienda, entrada, interés y años, y calcula la cuota mensual, el total a pagar y los intereses. |
| **Precheck de elegibilidad** | Una regresión logística entrenada con `Risk.xlsx` da una orientación sobre si el perfil sería apto. No aprueba ni deniega nada, es solo un ejercicio. |
| **Detector de operación** | Entiende frases como "simúlame una hipoteca" o "¿puedo pedir una hipoteca?" sin comandos exactos. Se puede cambiar de operación a mitad de proceso y para salir se escribe «cancelar». |

## Estructura del proyecto

```
lucIA/
├── app.py                      # app de Streamlit (el chat)
├── requirements.txt
├── requirements-lock.txt
│
├── lucia/                      # lógica del asistente
│   ├── conexion_clasificador.py    # conecta la app con BETO
│   ├── conexion_rag.py             # conecta la app con el RAG
│   ├── detector_operacion.py       # simular, precheck o consulta
│   ├── flujo_hipoteca.py           # preguntas paso a paso de la simulación
│   ├── calculadora_hipoteca.py     # fórmula de la cuota
│   ├── flujo_precheck.py           # preguntas paso a paso del precheck
│   └── precheck_hipoteca.py        # modelo de elegibilidad
│
├── datos/
│   └── Risk.xlsx               # datos del precheck
│
├── clasificador/               # entrenamiento y uso de BETO (con su propio README)
│   ├── data/                   # train / val / test
│   ├── models/                 # modelo entrenado
│   ├── results/                # métricas y errores
│   └── src/
│
└── Preguntas_frecuentes/       # RAG
    ├── datos/                  # PDFs
    ├── indice/                 # chunks y vectores ya calculados
    ├── evaluacion/             # preguntas de prueba
    └── rag/                    # cargar, limpiar, trocear, embeddings, búsqueda
```

## Cómo funciona el RAG

La idea es que el asistente conteste solo con lo que pone en los documentos y diga de dónde lo ha sacado.

1. Se leen los 34 PDFs con PyMuPDF, se limpian (quito pies de página y números por el tamaño de la letra) y se parten en fragmentos. Cada fragmento es un artículo entero, así que tiene un identificador (`AC-xxx`) que se puede citar. Salen 238 fragmentos.
2. Cada fragmento se convierte en un vector con `intfloat/multilingual-e5-small`.
3. Cuando llega una pregunta, se compara con todos los vectores y se cogen los 5 más parecidos. Con tan pocos fragmentos no hace falta una base de datos vectorial, con numpy basta.
4. Si ni el mejor fragmento llega a una similitud de 0,82, se considera que la pregunta no es del banco y se devuelve un texto fijo sin llamar al modelo, para que no se invente nada.
5. Si pasa, el modelo local (`qwen2.5:3b` con Ollama) responde usando solo esos fragmentos y cita los `AC-xxx`.

El índice ya está guardado en `Preguntas_frecuentes/indice`, así que no hace falta recalcularlo al arrancar.

**Lo que he medido** con 86 preguntas que escribí yo para probarlo:

- El artículo correcto sale entre los 5 primeros en el 89,5 % de los casos (91,9 % si se acepta cualquiera de los artículos válidos). Por eso uso k = 5.
- Con el umbral de 0,82 se aceptan 85 de 86 preguntas del banco, pero solo se rechazan 8 de 15 preguntas fuera de tema. El umbral ayuda, pero no es perfecto.

Como las preguntas las escribí yo y las uso también para elegir k y el umbral, estos números seguramente son mejores de lo que serían con preguntas de clientes reales.

Todas las decisiones, lo que descarté, las limitaciones y los fallos que encontré están en [`Preguntas_frecuentes/rag/README.md`](Preguntas_frecuentes/rag/README.md).

## Resultados del clasificador

Evaluado con el conjunto de test (258 frases que no se usaron para entrenar ni para elegir el umbral):

| Métrica | Valor |
|---|---|
| Accuracy | 0.988 |
| Precision | 0.973 |
| Recall | 1.000 |
| F1 | 0.986 |

Se equivoca en 3 frases de 258, y las 3 son "otro" clasificadas como hipoteca. Las métricas completas y cómo entrenarlo están en [`clasificador/README.md`](clasificador/README.md).

## Cómo ejecutarlo

Necesitas Python 3.10, 3.11 o 3.12 y [Ollama](https://ollama.com) instalado.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

ollama pull qwen2.5:3b

streamlit run app.py
```

En Linux o Mac el entorno se activa con `source .venv/bin/activate`.

La primera vez tarda un poco porque descarga el modelo de embeddings de Hugging Face. Ollama tiene que estar abierto cuando uses la app.

## Limitaciones

- Los PDFs son de ejemplo y el RAG solo sabe lo que pone en ellos. No tiene documentos de hipotecas, así que las preguntas generales sobre hipotecas se contestan con la información de atención al cliente.
- El precheck se entrena con pocos datos y el umbral (0.60) es ilustrativo. No sirve para decisiones reales.
- Un modelo de 3B parámetros en local a veces responde peor que uno grande.
- El clasificador solo distingue entre hipoteca y otro.

## Tecnologías

Python, Streamlit, PyTorch, Transformers (BETO), sentence-transformers, PyMuPDF, scikit-learn, pandas, Ollama.
