import os
import requests
import pandas as pd
from datetime import date, timedelta, datetime
from groq import Groq 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import random 
import uvicorn
import time 

# --- 1. CONFIGURAZIONE ---
API_KEY = "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" 
LAT, LON = 40.8518, 14.2681 

# --- CONFIGURAZIONE SERVER API ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SISTEMA DI CACHE ---
CACHE_DATI = None   
LAST_CALL = 0       
CACHE_DURATION = 180 # 3 Minuti

@app.get("/api/dati")
def genera_dati_per_frontend():
    global CACHE_DATI, LAST_CALL
    
    # --- 0. CONTROLLO CACHE ---
    now = time.time()
    if CACHE_DATI is not None and (now - LAST_CALL < CACHE_DURATION):
        tempo_rimanente = int(CACHE_DURATION - (now - LAST_CALL))
        print(f"🔄 CACHE ATTIVA: Restituisco dati salvati. ({tempo_rimanente}s rimanenti)")
        return CACHE_DATI 
    
    print("\n" + "🚀 NUOVA CHIAMATA API REALE (Cache scaduta)...".center(60, "="))

    # --- 1. PREPARAZIONE DATI ---
    # MODALITÀ UTENTE STANDARD
    TIPO_PROFILO = "UTENTE"
    
    oggi = date.today()
    sette_giorni_fa = oggi - timedelta(days=7)
    dopodomani = oggi + timedelta(days=2) 
    str_inizio = sette_giorni_fa.strftime("%Y-%m-%d")
    str_fine_previsione = dopodomani.strftime("%Y-%m-%d")

    print(f"📡 Scarico dati Meteo Completi...")

    # Variabili per il Frontend
    temp_attuale = 0
    umidita_attuale = 0
    vento_attuale = 0
    condizione_frontend = "NORMALE"
    lista_previsioni = []
    grafico_orari = []
    grafico_valori = []

    try:
        # AGGIUNTO 'hourly' per le card previsioni e 'wind_speed_10m' in current
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&start_date={str_inizio}&end_date={str_fine_previsione}&daily=temperature_2m_max,precipitation_sum,wind_speed_10m_max,apparent_temperature_max&current=temperature_2m,relative_humidity_2m,wind_speed_10m&hourly=temperature_2m,weather_code&timezone=Europe%2FBerlin"
        
        r = requests.get(url, timeout=10)
        data = r.json()
        
        # --- DATI PER AI (CSV) ---
        df_meteo = pd.DataFrame({
            'Data': data['daily']['time'], 
            'T_Percepita_Max': data['daily']['apparent_temperature_max'],
            'Pioggia_mm': data['daily']['precipitation_sum'],
            'Vento_Max_kmh': data['daily']['wind_speed_10m_max']
        })
        csv_storico = df_meteo.head(5).to_csv(index=False) # Simuliamo storico
        csv_futuro = df_meteo.to_csv(index=False)
        print("✅ Dati Meteo ricevuti.")

        # --- ESTRAZIONE DATI LIVE ---
        if 'current' in data:
            temp_attuale = data['current']['temperature_2m']
            umidita_attuale = data['current']['relative_humidity_2m']
            vento_attuale = data['current'].get('wind_speed_10m', 0)
            
            if temp_attuale > 30 or data['daily']['wind_speed_10m_max'][0] > 40:
                condizione_frontend = "ALLERTA"

        # --- GENERAZIONE PREVISIONI 48H (CARD) ---
        # Prendiamo i dati orari e ne estraiamo alcuni per le card
        raw_times = data['hourly']['time']
        raw_temps = data['hourly']['temperature_2m']
        raw_codes = data['hourly']['weather_code']
        
        # Cerchiamo l'indice dell'ora corrente per partire da adesso
        ora_adesso_str = datetime.now().strftime("%Y-%m-%dT%H:00")
        start_idx = 0
        for i, t in enumerate(raw_times):
            if t >= ora_adesso_str:
                start_idx = i
                break
        
        # Creiamo 6 card (una ogni 4 ore)
        for i in range(0, 24, 4): 
            idx = start_idx + i
            if idx < len(raw_times):
                dt = datetime.strptime(raw_times[idx], "%Y-%m-%dT%H:%M")
                is_rain = raw_codes[idx] > 50 # Codici pioggia open-meteo
                lista_previsioni.append({
                    "giorno": dt.strftime("%d %b"),
                    "ora": dt.strftime("%H:00"),
                    "temp": raw_temps[idx],
                    "icona": "cloud-rain" if is_rain else "sun"
                })

        # --- DATI GRAFICO (Prossime 12 ore reali) ---
        grafico_valori = raw_temps[start_idx : start_idx+12]
        grafico_orari = [t[-5:] for t in raw_times[start_idx : start_idx+12]] # Prende solo HH:MM

    except Exception as e:
        print(f"❌ Errore API: {e}")
        return {"errore": str(e)}

    # --- 2. LOGICA AI (GROQ) ---
    print(f"🤖 Configurazione AI per profilo: {TIPO_PROFILO}...")
    client = Groq(api_key=API_KEY)

    prompt_sicurezza = f"""
    Analizza questi dati meteo di Napoli:
    PREVISIONI: {csv_futuro}
    
    Genera un avviso di sicurezza BREVE (max 20 parole) e IMPERATIVO per i cittadini.
    Esempio: "Attenzione al vento forte, evitare parchi e zone costiere."
    """

    ai_response_text = "Dati AI non disponibili."

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Sei un sistema di allerta civile."},
                {"role": "user", "content": prompt_sicurezza}
            ],
            temperature=0.1, 
        )
        ai_response_text = completion.choices[0].message.content
        print(f"📋 RISPOSTA AI GENERATA: {ai_response_text[:50]}...")

    except Exception as e:
        print(f"❌ ERRORE AI: {e}")
        ai_response_text = "⚠️ Sistema AI Offline (Rate Limit). Prudenza consigliata."

    # --- 3. PREPARAZIONE PACCHETTO JSON (STRUTTURA CORRETTA) ---
    # Qui rinomino le chiavi per farle coincidere con il tuo JavaScript
    
    payload_finale = {
        "live": {   # PRIMA ERA "meteo", ORA È "live" PER IL JS
            "temp": temp_attuale,
            "umidita": umidita_attuale,
            "vento": vento_attuale, # Aggiunto vento
            "citta": "Napoli",
            "condizione": condizione_frontend
        },
        "ia_advice": ai_response_text,
        "grafico": { # PRIMA ERA "grafico_ospedali", ORA È "grafico"
            "orari": grafico_orari,
            "valori": grafico_valori
        },
        "previsioni_48h": lista_previsioni, # NUOVO: Serve per le card
        "mappa": [
            {"nome": "Centro Storico", "lat": 40.8518, "lng": 14.2681, "valore": temp_attuale + 1, "rischio": "alto" if temp_attuale > 30 else "medio"},
            {"nome": "Vomero", "lat": 40.8440, "lng": 14.2290, "valore": temp_attuale - 2, "rischio": "basso"}
        ]
    }

    # Salvataggio Cache
    CACHE_DATI = payload_finale
    LAST_CALL = time.time()
    
    return payload_finale

if __name__ == "__main__":
    print("🚀 Avvio Server AI Meteo...")
    uvicorn.run(app, host="127.0.0.1", port=8000)