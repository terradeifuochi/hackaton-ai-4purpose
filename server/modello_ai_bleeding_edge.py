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

# Configurazione CORS (Per far parlare il server con il sito)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache semplice per non finire i token dell'AI subito
CACHE_DATI = None
LAST_CALL = 0
CACHE_DURATION = 300 # 5 minuti di cache

@app.get("/api/dati")
def ottieni_dati_reali():
    global CACHE_DATI, LAST_CALL
    
    # Controllo Cache
    now = time.time()
    if CACHE_DATI is not None and (now - LAST_CALL < CACHE_DURATION):
        print("🔄 Restituisco dati dalla CACHE (Risparmio API)")
        return CACHE_DATI

    print("🚀 Scarico NUOVI dati Reali + AI...")

    # --- 2. RECUPERO DATI METEO (ESTESO A 48H) ---
    oggi = date.today()
    str_oggi = oggi.strftime("%Y-%m-%d")
    
    # Prendiamo dati da ieri a +3 giorni per avere copertura totale oraria
    str_inizio = (oggi - timedelta(days=1)).strftime("%Y-%m-%d")
    str_fine = (oggi + timedelta(days=3)).strftime("%Y-%m-%d")

    try:
        # Aggiungiamo 'hourly' per popolare grafici e card a 48h
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&start_date={str_inizio}&end_date={str_fine}&daily=temperature_2m_max,precipitation_sum,wind_speed_10m_max,apparent_temperature_max&current=temperature_2m,relative_humidity_2m,wind_speed_10m&hourly=temperature_2m,weather_code&timezone=Europe%2FBerlin"
        
        r = requests.get(url, timeout=10)
        data = r.json()

        # 1. DATI LIVE (Per la sezione in alto)
        temp_live = data['current']['temperature_2m']
        umidita_live = data['current']['relative_humidity_2m']
        vento_live = data['current']['wind_speed_10m']
        
        # Calcolo livello allerta basico
        allerta_live = "VERDE"
        if temp_live > 30: allerta_live = "GIALLA"
        if temp_live > 35: allerta_live = "ARANCIONE"
        if temp_live > 38: allerta_live = "ROSSA"

        # 2. DATI PER L'AI (Creiamo il CSV come nel tuo script nuovo)
        df_daily = pd.DataFrame({
            'Data': data['daily']['time'], 
            'T_Max': data['daily']['temperature_2m_max'],
            'T_Percepita': data['daily']['apparent_temperature_max'],
            'Pioggia': data['daily']['precipitation_sum'],
            'Vento_Max': data['daily']['wind_speed_10m_max']
        })
        csv_per_ai = df_daily.to_csv(index=False)

        # 3. ELABORAZIONE 48H (Per Grafico e Card)
        # Dobbiamo estrarre i dati orari specifici per le prossime ore
        raw_hours = data['hourly']['time']
        raw_temps = data['hourly']['temperature_2m']
        raw_codes = data['hourly']['weather_code']

        # Troviamo l'indice dell'ora attuale
        ora_corrente_str = datetime.now().strftime("%Y-%m-%dT%H:00")
        start_index = 0
        for i, t in enumerate(raw_hours):
            if t >= ora_corrente_str:
                start_index = i
                break
        
        # Generiamo le liste per il JSON
        lista_card_48h = []
        grafico_labels = []
        grafico_valori = []

        # Prendiamo 8 step (ogni 4 ore) per coprire circa 32-40 ore
        for i in range(0, 32, 4): 
            idx = start_index + i
            if idx < len(raw_hours):
                dt_obj = datetime.strptime(raw_hours[idx], "%Y-%m-%dT%H:%M")
                temp_val = raw_temps[idx]
                code_val = raw_codes[idx]

                # Icona semplificata
                icona = "sun"
                if code_val > 3: icona = "cloud-sun"
                if code_val > 50: icona = "cloud-rain"
                if temp_val > 35: icona = "flame"

                # Etichetta giorno (Domani/Dopodomani o nome giorno)
                giorno_lbl = dt_obj.strftime("%d/%m")
                if dt_obj.date() == date.today() + timedelta(days=1): giorno_lbl = "Domani"
                elif dt_obj.date() == date.today() + timedelta(days=2): giorno_lbl = "Dopodomani"

                # Popola Card
                lista_card_48h.append({
                    "giorno": giorno_lbl,
                    "ora": dt_obj.strftime("%H:00"),
                    "temp": temp_val,
                    "icona": icona
                })

                # Popola Grafico
                grafico_labels.append(dt_obj.strftime("%H:00"))
                grafico_valori.append(temp_val)

    except Exception as e:
        print(f"❌ Errore Meteo: {e}")
        return {"error": str(e)}

    # --- 3. CHIAMATA AI (GROQ) ---
    print("🤖 Interrogo l'Intelligenza Artificiale...")
    client = Groq(api_key=API_KEY)

    prompt_sicurezza = f"""
    Sei il Sistema A.I.D.A. di Napoli.
    Analizza questi dati: {csv_per_ai}
    Dati attuali: {temp_live}°C.
    
    Genera un CONSIGLIO DIRETTO e IMPERATIVO (Max 25 parole) per la popolazione basato sui pericoli (Caldo, Vento o Pioggia) dei prossimi 2 giorni.
    Non usare Markdown.
    """

    ia_advice_text = "Dati in elaborazione..."
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Sei un'IA di protezione civile."},
                {"role": "user", "content": prompt_sicurezza}
            ],
            temperature=0.1, 
        )
        ia_advice_text = completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Errore AI: {e}")
        ia_advice_text = "⚠️ Servizio AI momentaneamente non disponibile. Consultare bollettini ufficiali."

    # --- 4. COSTRUZIONE RISPOSTA JSON (FORMATO VECCHIO SERVER) ---
    response_payload = {
        "live": {
            "temp": temp_live,
            "umidita": umidita_live,
            "vento": vento_live,
            "citta": "Napoli",
            "allerta": allerta_live
        },
        "ia_advice": ia_advice_text,
        "previsioni_48h": lista_card_48h, # Ora contiene dati reali spaziati nel tempo
        "mappa": [
            # Napoli è Reale, gli altri sono simulati basandosi su Napoli per popolare la mappa
            {"nome": "Napoli Centro", "lat": 40.8518, "lng": 14.2681, "rischio": allerta_live.lower(), "valore": temp_live},
            {"nome": "Vomero (Collinare)", "lat": 40.8425, "lng": 14.2311, "rischio": "medio", "valore": round(temp_live - 2, 1)},
            {"nome": "Zona Industriale", "lat": 40.8550, "lng": 14.3000, "rischio": "alto", "valore": round(temp_live + 1, 1)}
        ],
        "grafico": {
            "orari": grafico_labels,
            "valori": grafico_valori
        }
    }

    # Salva in cache
    CACHE_DATI = response_payload
    LAST_CALL = time.time()

    return response_payload

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)