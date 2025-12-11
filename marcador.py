from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# Modelo para cuando el usuario añade un marcador al mapa
class Marcador(BaseModel):
    email_usuario: EmailStr     # El dueño del mapa
    ciudad_pais: str            # Nombre del sitio (ej: "Madrid, España")
    latitud: float              # Coordenada
    longitud: float             # Coordenada
    imagen_url: Optional[str] = None # URL de la foto en Cloudinary (opcional al principio)