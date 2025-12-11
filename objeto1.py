from datetime import datetime
from pydantic import BaseModel
from typing import List

class Objeto1(BaseModel):
    clave1: str
    lista1: List[str]  
    descripcion: str
    booleano: bool
    fecha: datetime
    entero: int
    objeto2: List[str]