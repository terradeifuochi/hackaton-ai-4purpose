from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import random

app = FastAPI()

# Questo blocco serve a dire: "Accetta connessioni da chiunque (anche dal file html sul desktop)"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/dati")
def ottieni_dati():
    # QUI SIMULIAMO L'INTELLIGENZA ARTIFICIALE
    # In un caso reale, qui ci sarebbero i calcoli veri.
    
    return {
        "meteo": {
            "temp": 39.5,
            "umidita": 72,
            "condizione": "Estrema",
            "citta": "Napoli"
        },
        "mappa": [
            {"nome": "Napoli Centro", "lat": 40.8518, "lng": 14.2681, "rischio": "alto", "valore": 41},
            {"nome": "Vomero", "lat": 40.8425, "lng": 14.2311, "rischio": "medio", "valore": 37},
            {"nome": "Secondigliano", "lat": 40.8926, "lng": 14.2616, "rischio": "alto", "valore": 40}
        ],
        "grafico_ospedali": {
            "orari": ["10:00", "12:00", "14:00", "16:00", "18:00", "20:00"],
            "valori": [20, 45, 95, 130, 85, 50] # Picco alle 16:00
        },
        "ia_advice": "L'analisi predittiva incrociata con i dati satellitari Copernicus segnala un'isola di calore critica a Napoli Centro. Si consiglia attivazione protocollo 'Codice Argento' per gli over-75."
    }

if __name__ == "__main__":
    print("Server IA avviato su http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)