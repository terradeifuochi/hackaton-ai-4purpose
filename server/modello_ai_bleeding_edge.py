import os
import requests
import pandas as pd
from datetime import date, timedelta, datetime
from groq import Groq 
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

CACHE_DATI = None
LAST_CALL = 0
CACHE_DURATION = 300 

@app.get("/api/dati")
def ottieni_dati_reali():
    global CACHE_DATI, LAST_CALL
    
    now = time.time()
    
    # Controllo Cache: verifico se esiste e se ha i nuovi campi (umidita e vento nelle card)
    # Se manca qualcosa, ricarica tutto.
    if (CACHE_DATI is not None 
        and (now - LAST_CALL < CACHE_DURATION) 
        and 'pioggia_prob' in CACHE_DATI['live']):
        
        # Controllo extra per essere sicuri che le card abbiano i nuovi dati
        if len(CACHE_DATI['previsioni_48h']) > 0 and 'umidita' in CACHE_DATI['previsioni_48h'][0]:
            print("🔄 CACHE VALIDA: Invio dati salvati.")
            return CACHE_DATI

    print("🚀 RECUPERO NUOVI DATI COMPLETI (Temp, Pioggia, Vento, Umidità)...")

    oggi = date.today()
    str_inizio = (oggi - timedelta(days=1)).strftime("%Y-%m-%d")
    str_fine = (oggi + timedelta(days=3)).strftime("%Y-%m-%d")

    try:
        # AGGIUNTO: wind_speed_10m e relative_humidity_2m in hourly
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&start_date={str_inizio}&end_date={str_fine}&daily=temperature_2m_max,precipitation_sum,wind_speed_10m_max,apparent_temperature_max&current=temperature_2m,relative_humidity_2m,wind_speed_10m&hourly=temperature_2m,weather_code,precipitation_probability,wind_speed_10m,relative_humidity_2m&timezone=Europe%2FBerlin"
        
        r = requests.get(url, timeout=10)
        data = r.json()

        # 1. DATI LIVE
        temp_live = data['current']['temperature_2m']
        umidita_live = data['current']['relative_humidity_2m']
        vento_live = data['current']['wind_speed_10m']
        
        allerta_live = "VERDE"
        if temp_live > 30: allerta_live = "GIALLA"
        if temp_live > 35: allerta_live = "ARANCIONE"
        if temp_live > 38: allerta_live = "ROSSA"
        if vento_live > 60: allerta_live = "ROSSA"

        # 2. DATI PER AI
        df_daily = pd.DataFrame({
            'Data': data['daily']['time'], 
            'T_Max': data['daily']['temperature_2m_max'],
            'T_Percepita': data['daily']['apparent_temperature_max'],
            'Pioggia': data['daily']['precipitation_sum'],
            'Vento_Max': data['daily']['wind_speed_10m_max']
        })
        csv_per_ai = df_daily.to_csv(index=False)

        # 3. ELABORAZIONE 48H + DETTAGLI
        raw_hours = data['hourly']['time']
        raw_temps = data['hourly']['temperature_2m']
        raw_codes = data['hourly']['weather_code']
        raw_probs = data['hourly']['precipitation_probability']
        raw_winds = data['hourly']['wind_speed_10m']       # NUOVO
        raw_hums = data['hourly']['relative_humidity_2m']   # NUOVO

        ora_corrente_str = datetime.now().strftime("%Y-%m-%dT%H:00")
        start_index = 0
        for i, t in enumerate(raw_hours):
            if t >= ora_corrente_str:
                start_index = i
                break
        
        # Live Prob Pioggia
        pioggia_prob_live = 0
        if start_index < len(raw_probs):
            pioggia_prob_live = raw_probs[start_index]
        
        lista_card_48h = []
        grafico_labels = []
        grafico_valori = []

        for i in range(0, 48, 4): 
            idx = start_index + i
            if idx < len(raw_hours):
                dt_obj = datetime.strptime(raw_hours[idx], "%Y-%m-%dT%H:%M")
                temp_val = raw_temps[idx]
                code_val = raw_codes[idx]
                
                # Icona
                icona = "sun"
                if code_val > 3: icona = "cloud-sun"
                if code_val > 45: icona = "cloud-fog"
                if code_val > 50: icona = "cloud-rain"
                if temp_val > 35: icona = "flame"

                giorno_lbl = dt_obj.strftime("%d/%m")
                if dt_obj.date() == date.today() + timedelta(days=1): giorno_lbl = "Domani"
                elif dt_obj.date() == date.today() + timedelta(days=2): giorno_lbl = "Dopodomani"
                elif dt_obj.date() == date.today(): giorno_lbl = "Oggi"

                lista_card_48h.append({
                    "giorno": giorno_lbl,
                    "ora": dt_obj.strftime("%H:00"),
                    "temp": temp_val,
                    "icona": icona,
                    "pioggia": raw_probs[idx], # NUOVO
                    "vento": raw_winds[idx],   # NUOVO
                    "umidita": raw_hums[idx]   # NUOVO
                })

                grafico_labels.append(dt_obj.strftime("%d/%m %H:00"))
                grafico_valori.append(temp_val)

    except Exception as e:
        print(f"❌ Errore Meteo: {e}")
        return {"error": str(e)}

    # --- 3. CHIAMATA AI ---
    print("🤖 Interrogo AI...")
    client = Groq(api_key=API_KEY)
    
    prompt = f"""
    Analizza meteo Napoli.
    Dati: {csv_per_ai}
    Live: {temp_live}°C, Vento {vento_live}km/h, Pioggia Prob {pioggia_prob_live}%.
    Consiglio IMPERATIVO breve (Max 20 parole).
    """

    ia_text = "..."
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        ia_text = completion.choices[0].message.content
    except:
        ia_text = "AI momentaneamente offline."

    # --- 4. RISPOSTA JSON ---
    response_payload = {
        "live": {
            "temp": temp_live,
            "umidita": umidita_live,
            "vento": vento_live,
            "pioggia_prob": pioggia_prob_live,
            "citta": "Napoli (Stazione)",
            "allerta": allerta_live
        },
        "ia_advice": ia_text,
        "previsioni_48h": lista_card_48h, 
        "mappa": [
            {"nome": "Stazione Rilevamento", "lat": LAT, "lng": LON, "rischio": allerta_live.lower(), "valore": temp_live}
        ],
        "grafico": {
            "orari": grafico_labels,
            "valori": grafico_valori
        }
    }

    CACHE_DATI = response_payload
    LAST_CALL = time.time()
    return response_payload

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)