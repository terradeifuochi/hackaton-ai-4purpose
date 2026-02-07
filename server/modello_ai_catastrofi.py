import os
import requests
import pandas as pd
from datetime import date, timedelta, datetime
from groq import Groq, RateLimitError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import time

# --- 1. CONFIGURAZIONE ---
API_KEY = "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" 
LAT, LON = 40.8518, 14.2681 
CSV_FILE = "server/dati_disastrosi.csv"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/dati")
def ottieni_dati_reali():
    print(f"🚀 RICHIESTA RICEVUTA: Recupero dati dal CSV {CSV_FILE}...")

    try:
        # LETTURA CSV
        if not os.path.exists(CSV_FILE):
            return {"error": f"File {CSV_FILE} non trovato!"}
        
        df = pd.read_csv(CSV_FILE)
        
        # Estraiamo i dati dalla prima riga (Simuliamo il LIVE)
        live_row = df.iloc[0]
        temp_live = float(live_row['T_Reale_Max'])
        umidita_live = 45.0  # Dato fisso se non presente nel tuo CSV
        vento_live = float(live_row['Vento_Max_kmh'])
        pioggia_prob_live = 100 if float(live_row['Pioggia_mm']) > 10 else 20

        # LOGICA ALLERTA REALE
        allerta_live = "VERDE"
        if temp_live >= 39 or vento_live >= 80: 
            allerta_live = "ROSSA"
        elif temp_live >= 36 or vento_live >= 60: 
            allerta_live = "ARANCIONE"
        elif temp_live >= 32 or vento_live >= 40: 
            allerta_live = "GIALLA"
        else: 
            allerta_live = "VERDE"

        # ELABORAZIONE "PREVISIONI" (usando le righe del CSV)
        lista_card_48h = []
        grafico_labels = []
        grafico_valori = []

        for i in range(len(df)):
            row = df.iloc[i]
            data_str = row['Data']
            temp_val = float(row['T_Reale_Max'])
            vento_val = float(row['Vento_Max_kmh'])
            pioggia_val = float(row['Pioggia_mm'])

            # Icona dinamica
            icona = "sun"
            if pioggia_val > 5: icona = "cloud-rain"
            if temp_val > 35: icona = "flame"

            lista_card_48h.append({
                "giorno": data_str,
                "ora": "Max",
                "temp": temp_val,
                "icona": icona,
                "pioggia": pioggia_val,
                "vento": vento_val,
                "umidita": 45 # Default
            })
            
            grafico_labels.append(data_str)
            grafico_valori.append(temp_val)

        # CHIAMATA AI
        client = Groq(api_key=API_KEY)
        prompt = f"Meteo Napoli (SIM): {temp_live}C, Vento {vento_live}kmh, Pioggia {pioggia_prob_live}%. Dai un consiglio di sicurezza di 15 parole."
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            ia_text = completion.choices[0].message.content
        except RateLimitError as e:
            ia_text = "Troppe richieste. Riprova tra un momento."
        except Exception as e:
            ia_text = "Monitoraggio attivo. Seguire le norme di prudenza."
            
        return {
            "live": {
                "temp": temp_live,
                "umidita": umidita_live,
                "vento": vento_live,
                "pioggia_prob": pioggia_prob_live,
                "citta": "Napoli (CSV)",
                "allerta": allerta_live
            },
            "ia_advice": ia_text,
            "previsioni_48h": lista_card_48h, 
            "mappa": [{"nome": "Rilevamento Napoli", "lat": LAT, "lng": LON, "rischio": allerta_live, "valore": temp_live}],
            "grafico": {"orari": grafico_labels, "valori": grafico_valori}
        }

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)