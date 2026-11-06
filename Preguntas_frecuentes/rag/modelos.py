
from dataclasses import dataclass


@dataclass
class Linea:
    texto: str
    tamano: float
    negrita: bool
    pagina: int
    bloque: int
    y: float = 0.0


@dataclass
class Chunk:
    id: str
    texto: str
    seccion: str
    documento: str
    pagina: int