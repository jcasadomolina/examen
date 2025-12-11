from datetime import datetime
from pydantic import BaseModel, Field
from typing import List

class Usuario(BaseModel):
    email: str