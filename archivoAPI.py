from fastapi import FastAPI, Response, Body , HTTPException, UploadFile, File        # FastAPI
from archivo import Archivo
from bson import ObjectId
import motor.motor_asyncio as motor
from environs import Env
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import cloudinary
from contextlib import asynccontextmanager
import cloudinary.uploader
"""
url_calendario = "http://localhost:8000/"
url_evento = "http://localhost:8001/"
url_comentario = "http://localhost:8002/"
url_mapas = "http://localhost:8003/"
url_archivos = "http://localhost:8004/"
url_frontend = "http://localhost:8005/"
url_notificaciones = "http://localhost:8006/"
"""

url_calendario = "http://calendario-service:8000/"
url_evento = "http://evento-service:8000/"
url_comentario = "http://comentario-service:8000/"
url_mapas = "http://mapa-service:8000/"
url_archivos = "http://archivo-service:8000/"
url_frontend = "http://localhost:8005/"
url_notificaciones = "http://notificacion-service:8000/"


env = Env()
env.read_env()
uri = env('MONGO_URI')

cloudinary.config( 
    cloud_name = env('CLOUDINARY_CLOUD_NAME'), 
    api_key = env('CLOUDINARY_API_KEY'), 
    api_secret = env('CLOUDINARY_API_SECRET'),
    secure = True
)

nombre_basedatos = "KalendasV2"
nombre_coleccion = "Archivos"

client = motor.AsyncIOMotorClient(uri)
database = client[nombre_basedatos][nombre_coleccion]


app = FastAPI()

origins = [
    # Incluir el origen exacto que está dando el error
    "http://127.0.0.1:8000",  
    "http://localhost:8000",
    "http://127.0.0.1:8001",  
    "http://localhost:8001", 
    "http://127.0.0.1:8002",  
    "http://localhost:8002",
    "http://127.0.0.1:8003",  
    "http://localhost:8003",
    "http://127.0.0.1:8004",  
    "http://localhost:8004",
    "http://127.0.0.1:8005",  
    "http://localhost:8005",
    "http://127.0.0.1:8006",
    "http://localhost:8006",
]

# --- CONFIGURACIÓN CORS PERMISIVA (SOLUCIÓN) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # <--- El asterisco permite CUALQUIER origen (IP/Puerto)
    allow_credentials=True,   # Permite cookies y credenciales
    allow_methods=["*"],      # Permite todos los métodos (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],      # Permite todos los headers (Content-Type, Authorization, etc.)
)

path = "/v2/archivo"


async def upload_image(archivo_id: str, file: UploadFile):
    try:
        # Regresamos el cursor al inicio por seguridad
        await file.seek(0)
        
        # CORRECCIÓN: Usamos 'public_id' y 'folder'
        # Quitamos el try/except silencioso para ver si falla aquí
        upload_result = cloudinary.uploader.upload(
            file.file,
            public_id=str(archivo_id),  # <--- CORREGIDO: public_id
            folder="archivos", # Carpeta en Cloudinary
            resource_type="auto"
        )
        
        return upload_result["secure_url"]

    except Exception as e:
        # Imprimimos el error REAL en la consola para que lo veas
        print(f"ERROR CLOUDINARY: {e}")
        # Re-lanzamos el error para que el endpoint se entere y falle
        raise e


@app.post(path)
async def crear_Archivo(file: UploadFile = File(...)):
    try:
        tipo = file.content_type
        # Limpieza del nombre del archivo
        nombre = os.path.basename(file.filename.replace("\\", "/")) if file.filename else "sin_nombre"
        
        body = {
            "nombre": nombre,
            "tipo": tipo,
            "enlace": ""
        }
        
        insert_result = await database.insert_one(body)
        archivo_id = insert_result.inserted_id
        
        url_imagen = await upload_image(str(archivo_id), file)


        await database.update_one(
            {"_id": archivo_id}, 
            {"$set": {"enlace": url_imagen}}
        )
        
        body["enlace"] = url_imagen
        body["_id"] = str(archivo_id)

        return {"mensaje": "Archivo insertado correctamente", "archivo": body}

    except Exception as e:

        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get(path + "/ver/{archivo_id}")
async def redireccionar_Al_Archivo(archivo_id:str):
    try:
        obj_id = ObjectId(archivo_id)
    except:
         raise HTTPException(status_code=400, detail="ID inválido")

    archivo = await database.find_one({"_id": obj_id})
    if not archivo:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
    enlace = archivo.get("enlace")
    if not enlace:
        raise HTTPException(status_code=404, detail="El archivo existe pero no tiene imagen asociada")
        
    return RedirectResponse(url=enlace)


#GET UNO R
@app.get(path+"/{archivo_id}")
async def obtener_Archivo(archivo_id: str) -> Archivo:
    try:
        id = ObjectId(archivo_id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")
    
    docs = await database.find_one({"_id":id})
    if not docs:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    del docs["_id"]
    archivo = Archivo(**docs)
    
    return archivo



@app.delete(path + "/{archivo_id}")
async def eliminar_Archivo(archivo_id: str):
    try:
        obj_id = ObjectId(archivo_id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido")

    archivo = await database.find_one({"_id": obj_id})
    if not archivo:
        raise HTTPException(status_code=404, detail="Archivo no encontrado en BD")

    # --- BLOQUE DE BORRADO CLOUDINARY MEJORADO ---
    try:
        # 1. Construimos el ID esperado
        public_id = f"archivos/{archivo_id}" #Ruta en Cloudinary
        
        # 2. Intentamos borrar el archivo en Cloudinary
        resultado_cloud = cloudinary.uploader.destroy(public_id)
        
        # Si la respuesta es 'not found', intentamos borrar sin la carpeta (para imágenes viejas)
        if resultado_cloud.get('result') == 'not found':
             print("No encontrado en carpeta 'archivos', intentando borrar en raíz...")
             resultado_cloud_root = cloudinary.uploader.destroy(archivo_id)
             print(f"Respuesta Cloudinary (Raíz): {resultado_cloud_root}")

    except Exception as e:
        print(f"ERROR CRÍTICO EN CLOUDINARY: {e}")
    # ---------------------------------------------

    resultado = await database.delete_one({"_id": obj_id})
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No se pudo borrar de la BD")

    return {"mensaje": "Archivo eliminado correctamente"}

#Me devuelve el enlace del archivo
@app.get(path+"/obtenerEnlace/{archivo_id}")
async def obtener_Enlace_Archivo(archivo_id: str) -> str:
    resultado = await database.find_one({"_id": ObjectId(archivo_id)})
    if resultado is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    del resultado["_id"]
    archivo = Archivo(**resultado)
    enlace = archivo.enlace
    return enlace

