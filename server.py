from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/dati")
def ottieni_dati():
    return {
        "live": {
            "temp": 39.5,
            "umidita": 72,
            "vento": 18,
            "citta": "Napoli",
            "allerta": "ROSSA"
        },
        
        # Consigli in alto per il cittadino
        "ia_advice": "Ondata di calore critica nelle prossime 48 ore. Evitare l'esposizione al sole tra le 12:00 e le 16:00. I punti di idratazione in centro sono attivi.",

        # Dati estesi per 48 ore (Domani e Dopodomani)
        "previsioni_48h": [
            {"giorno": "Domani", "ora": "08:00", "temp": 28, "icona": "sun"},
            {"giorno": "Domani", "ora": "12:00", "temp": 38, "icona": "sun"},
            {"giorno": "Domani", "ora": "16:00", "temp": 42, "icona": "flame"},
            {"giorno": "Domani", "ora": "20:00", "temp": 32, "icona": "cloud-sun"},
            {"giorno": "Dopodomani", "ora": "08:00", "temp": 30, "icona": "sun"},
            {"giorno": "Dopodomani", "ora": "12:00", "temp": 39, "icona": "sun"},
            {"giorno": "Dopodomani", "ora": "16:00", "temp": 43, "icona": "flame"}, # Picco massimo
            {"giorno": "Dopodomani", "ora": "20:00", "temp": 35, "icona": "cloud-sun"}
        ],

        "mappa": [
            {"nome": "Napoli Centro", "lat": 40.8518, "lng": 14.2681, "rischio": "alto", "valore": 41},
            {"nome": "Vomero", "lat": 40.8425, "lng": 14.2311, "rischio": "medio", "valore": 37},
            {"nome": "Portici", "lat": 40.8190, "lng": 14.3400, "rischio": "alto", "valore": 40}
        ],

        "grafico": {
            "orari": ["Dom 08", "Dom 12", "Dom 16", "Dom 20", "Dop 08", "Dop 12", "Dop 16", "Dop 20"],
            "valori": [28, 38, 42, 32, 30, 39, 43, 35] 
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)