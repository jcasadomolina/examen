from environs import Env
from fastapi import FastAPI, File, Form, Request, Depends, HTTPException, UploadFile, requests
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import motor.motor_asyncio as motor
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from marcador import Marcador
import requests
import cloudinary.uploader
import cloudinary

env = Env()
env.read_env()

uri = env('MONGO_URI')
client_id = env('CLIENT_ID')

client = motor.AsyncIOMotorClient(uri)
db = client["examen"]
coleccion1 = db["Coleccion1"]
mapas = db["Mapas"]
archivos = db["Archivos"]
marcadores = db["Marcadores"]

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key="SUPER_SECRET_KEY_RANDOM")
templates = Jinja2Templates(directory="templates")

cloudinary.config(cloud_name = env('NOMBRE'), api_key = env('API_KEY'), api_secret = env('API_SECRET'),secure = True)

path = "/path"


class TokenData(BaseModel):
    token: str

def get_user(request: Request):
    return request.session.get('user')


# Login de usuario con Google OAuth2
@app.post("/login")
async def login(data: TokenData, request: Request):
    try:
        id_info = id_token.verify_oauth2_token(
            data.token, 
            google_requests.Request(), 
            client_id
        )

        user_info = {
            "google_id": id_info.get("sub"),
            "email": id_info.get("email"),
            "name": id_info.get("name"),
            "picture": id_info.get("picture")
        }
        request.session['user'] = user_info
        
        return RedirectResponse(url='/mapa', status_code=303)

    except ValueError as e:
        print(f"Error validando token: {e}")
        raise HTTPException(status_code=401, detail="Token inválido")

# Logout de usuario
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url='/', status_code=303)


# Página principal
@app.get("/")
async def home(request: Request, user: dict = Depends(get_user)):
    return templates.TemplateResponse("home.html", {
        "request": request, 
        "user": user, 
        "client_id": client_id
    })

# Página del mapa con marcadores
@app.get("/mapa")
async def ver_mapa(request: Request, user: dict = Depends(get_user)):
    marcadores_list = []
    cursor = marcadores.find({"email": user["email"]})
    async for doc in cursor:
        marcadores_list.append({
            "ciudad": doc["ciudad"],
            "lat": doc["latitud"],
            "lon": doc["longitud"],
            "img": doc.get("imagen_url", "")
        })

    return templates.TemplateResponse("mapa.html", {
        "request": request,
        "email": user["email"],
        "marcadores": marcadores_list
    })

@app.post("/marcadores", tags=["Marcadores"])
async def crear_marcador(marcador: Marcador):
    marcador_dict = marcador.model_dump()
    
    await marcadores.insert_one(marcador_dict)
    
    return {"mensaje": "Marcador guardado correctamente", "marcador": marcador}

@app.get("/marcadores/{email}", tags=["Marcadores"])
async def obtener_marcadores(email: str):
    marcadores_list = []
    cursor = marcadores.find({"email": email})
    
    async for doc in cursor:
        if "_id" in doc:
            del doc["_id"]
        
        marcadores_list.append(Marcador(**doc))
        
    return marcadores_list

# Función para obtener coordenadas usando OpenStreetMap
def obtener_coordenadas(ciudad: str):
    """
    Usa la API gratuita de OpenStreetMap para obtener lat/lon.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": ciudad,
        "format": "json",
        "limit": 1
    }
    headers = {"User-Agent": "Examen/1.0"}
    
    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"])
    return None, None

# Endpoint para recibir el formulario del mapa
@app.post("/web/nuevo-marcador", tags=["Vistas"])
async def crear_marcador_web(
    request: Request,
    email: str = Form(...),       
    ciudad: str = Form(...),      
    imagen: UploadFile = File(...) 
):
    
    lat, lon = obtener_coordenadas(ciudad)
    
    if lat is None or lon is None:
        print(f"Error: No se encontraron coordenadas para {ciudad}")
        return RedirectResponse(url=f"/mapa", status_code=303)


    url_imagen = ""
    if imagen.filename:
        resultado = cloudinary.uploader.upload(imagen.file, folder="archivos")
        url_imagen = resultado.get("secure_url")

    nuevo_marcador = {
        "email": email,
        "ciudad": ciudad,
        "latitud": lat,
        "longitud": lon,
        "imagen_url": url_imagen
    }
    
    await marcadores.insert_one(nuevo_marcador)
    return RedirectResponse(url=f"/mapa?email={email}", status_code=303)