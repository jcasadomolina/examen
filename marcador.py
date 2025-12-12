from pydantic import BaseModel, EmailStr
from typing import Optional

class Marcador(BaseModel):
    email: EmailStr
    ciudad: str
    latitud: float
    longitud: float
    imagen_url: Optional[str] = None