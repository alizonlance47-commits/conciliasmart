from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import json
import pdfplumber
import io

load_dotenv()
client = OpenAI()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://resplendent-lebkuchen-2208.netlify.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PeticionConciliacion(BaseModel):
    desc_banco: str
    desc_contabilidad: str
    valor: float

class PeticionReporte(BaseModel):
    conciliados: int
    sugerencias: int
    pendientes: int
    empresa: str

@app.post("/api/conciliar-ia")
async def conciliar_ia(datos: PeticionConciliacion):
    prompt_sistema = """Eres un asistente contable. Compara un movimiento bancario y uno contable. 
    Responde solo en JSON con los campos coincide (true/false), confianza (0 a 100), 
    justificacion (texto breve) y requiere_revision (true/false)."""
    
    prompt_usuario = f"Banco: {datos.desc_banco}. Contabilidad: {datos.desc_contabilidad}. Valor: {datos.valor}"

    respuesta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        response_format={ "type": "json_object" }
    )
    return json.loads(respuesta.choices[0].message.content)

@app.post("/api/generar-reporte")
async def generar_reporte(datos: PeticionReporte):
    prompt = f"""Actúa como un Contador Público experto. Escribe un párrafo ejecutivo y profesional 
    para el informe de conciliación de la empresa '{datos.empresa}'. 
    Datos: {datos.conciliados} movimientos conciliados exitosamente, {datos.sugerencias} sugerencias pendientes de revisión, y {datos.pendientes} movimientos sin conciliar.
    El tono debe ser formal, analítico y sugerir acciones a tomar. No uses saludos, ve directo al grano."""

    respuesta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"reporte": respuesta.choices[0].message.content}

# NUEVO ENDPOINT PARA LEER PDFs
@app.post("/api/leer-pdf")
async def leer_pdf(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        rows = []
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        # Busca filas con al menos 3 columnas (Fecha, Tercero, Valor)
                        if row and len(row) >= 3:
                            rows.append({
                                "Fecha": row[0],
                                "Tercero": row[1],
                                "Valor": row[2]
                            })
        return {"status": "ok", "data": rows}
    except Exception as e:
        return {"status": "error", "message": str(e)}