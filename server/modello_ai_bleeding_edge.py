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
    print(f"🚀 RICHIESTA RICEVUTA: Recupero dati reali dal satellite...")

    oggi = date.today()
    str_inizio = (oggi - timedelta(days=1)).strftime("%Y-%m-%d")
    str_fine = (oggi + timedelta(days=3)).strftime("%Y-%m-%d")

    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&start_date={str_inizio}&end_date={str_fine}&daily=temperature_2m_max,precipitation_sum,wind_speed_10m_max,apparent_temperature_max&current=temperature_2m,relative_humidity_2m,wind_speed_10m&hourly=temperature_2m,weather_code,precipitation_probability,wind_speed_10m,relative_humidity_2m&timezone=Europe%2FBerlin"
        
        r = requests.get(url, timeout=10)
        data = r.json()

        # DATI LIVE
        temp_live = data['current']['temperature_2m']
        umidita_live = data['current']['relative_humidity_2m']
        vento_live = data['current']['wind_speed_10m']
        
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

        # ELABORAZIONE ORARIA
        raw_hours = data['hourly']['time']
        raw_temps = data['hourly']['temperature_2m']
        raw_codes = data['hourly']['weather_code']
        raw_probs = data['hourly']['precipitation_probability']
        raw_winds = data['hourly']['wind_speed_10m']
        raw_hums = data['hourly']['relative_humidity_2m']

        ora_corrente_str = datetime.now().strftime("%Y-%m-%dT%H:00")
        start_index = 0
        for i, t in enumerate(raw_hours):
            if t >= ora_corrente_str:
                start_index = i
                break
        
        pioggia_prob_live = raw_probs[start_index] if start_index < len(raw_probs) else 0

        lista_card_48h = []
        grafico_labels = []
        grafico_valori = []

        for i in range(0, 48, 4): 
            idx = start_index + i
            if idx < len(raw_hours):
                dt_obj = datetime.strptime(raw_hours[idx], "%Y-%m-%dT%H:%M")
                
                icona = "sun"
                if raw_codes[idx] > 50: icona = "cloud-rain"
                if raw_temps[idx] > 35: icona = "flame"

                giorno_lbl = "Oggi" if dt_obj.date() == oggi else "Domani" if dt_obj.date() == oggi + timedelta(days=1) else "Dopodomani"

                lista_card_48h.append({
                    "giorno": giorno_lbl,
                    "ora": dt_obj.strftime("%H:00"),
                    "temp": raw_temps[idx],
                    "icona": icona,
                    "pioggia": raw_probs[idx],
                    "vento": raw_winds[idx],
                    "umidita": raw_hums[idx]
                })
                grafico_labels.append(dt_obj.strftime("%H:00"))
                grafico_valori.append(raw_temps[idx])

        # CHIAMATA AI
        client = Groq(api_key=API_KEY)
        prompt = f"Meteo Napoli: {temp_live}C, Vento {vento_live}kmh, Pioggia {pioggia_prob_live}%. Dai un consiglio di sicurezza di 15 parole."
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                timeout=5.0
            )
            ia_text = completion.choices[0].message.content
        except RateLimitError as e:
            print(f"⚠️ RATE LIMIT RAGGIUNTO: {e}")
            ia_text = "Troppe richieste. Riprova tra un momento."
        except Exception as e:
            print(f"❌ ERRORE CRITICO AI: {str(e)}")
            ia_text = "Monitoraggio attivo. Seguire le norme di prudenza."
            
        return {
            "live": {
                "temp": temp_live,
                "umidita": umidita_live,
                "vento": vento_live,
                "pioggia_prob": pioggia_prob_live,
                "citta": "Napoli",
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