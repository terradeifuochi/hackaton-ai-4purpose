import os
import requests
import pandas as pd
from datetime import date, timedelta
from groq import Groq 
# --- AGGIUNTA PER SERVER ---
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import random 
import uvicorn
import time # AGGIUNTO: Fondamentale per il calcolo dei secondi

# --- 1. CONFIGURAZIONE ---
API_KEY = "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" 
LAT, LON = 40.8518, 14.2681 

# --- CONFIGURAZIONE SERVER API ---
app = FastAPI()

# Abilitiamo CORS per permettere al HTML di collegarsi
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SISTEMA DI CACHE (PER NON BRUCIARE API) ---
CACHE_DATI = None   # Qui salviamo l'ultima risposta
LAST_CALL = 0       # Quando abbiamo fatto l'ultima chiamata vera
CACHE_DURATION = 180 # 180 secondi = 3 Minuti

# --- QUESTA È LA FUNZIONE CHE VERRA CHIAMATO ---
@app.get("/api/dati")
def genera_dati_per_frontend():
    # Dichiaramo che vogliamo modificare le variabili globali
    global CACHE_DATI, LAST_CALL
    
    # --- 0. CONTROLLO CACHE (MODIFICA RICHIESTA) ---
    now = time.time()
    # Se esiste una cache E sono passati meno di 180 secondi dall'ultima chiamata
    if CACHE_DATI is not None and (now - LAST_CALL < CACHE_DURATION):
        tempo_rimanente = int(CACHE_DURATION - (now - LAST_CALL))
        print(f"🔄 CACHE ATTIVA: Restituisco dati salvati. Prossima chiamata reale tra {tempo_rimanente} secondi.")
        return CACHE_DATI # Restituisce subito i dati vecchi senza fare chiamate API
    
    # Se arriviamo qui, significa che dobbiamo scaricare dati nuovi
    print("\n" + "🚀 NUOVA CHIAMATA API REALE (Cache scaduta)...".center(60, "="))

    # --- SELEZIONE MODALITÀ ---
    TIPO_PROFILO = "UTENTE" 

    # --- 2. CARICAMENTO DATI STORICI ---
    print(f"📂 Avvio sistema in modalità: {TIPO_PROFILO}")
    print("📂 Controllo database storico locale...")

    csv_storico = "Nessun dato storico disponibile."

    if os.path.exists('dati_per_ai.csv'):
        try:
            df_storico = pd.read_csv('dati_per_ai.csv')
            csv_storico = df_storico.tail(30).to_csv(index=False)
            print("✅ Storico caricato (Ultimi 30 gg).")
        except Exception as e:
            print(f"⚠️ Errore storico: {e}")
    else:
        print("⚠️ File storico non trovato. Procedo senza.")

    # --- 3. RECUPERO METEO REALE ---
    oggi = date.today()
    str_oggi = oggi.strftime("%Y-%m-%d")

    sette_giorni_fa = oggi - timedelta(days=7)
    dopodomani = oggi + timedelta(days=2) 
    str_inizio = sette_giorni_fa.strftime("%Y-%m-%d")
    str_fine_previsione = dopodomani.strftime("%Y-%m-%d")

    print(f"📡 Scarico dati Meteo Completi...")

    # Variabili per il Frontend (inizializzate a default)
    temp_attuale = 0
    umidita_attuale = 0
    condizione_frontend = "NORMALE"

    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&start_date={str_inizio}&end_date={str_fine_previsione}&daily=temperature_2m_max,precipitation_sum,wind_speed_10m_max,apparent_temperature_max&current=temperature_2m,relative_humidity_2m&timezone=Europe%2FBerlin"
        
        r = requests.get(url, timeout=10)
        data = r.json()
        

        df_meteo = pd.DataFrame({
            'Data': data['daily']['time'], 
            'T_Percepita_Max': data['daily']['apparent_temperature_max'],
            'Pioggia_mm': data['daily']['precipitation_sum'],
            'Vento_Max_kmh': data['daily']['wind_speed_10m_max']
        })

        csv_futuro = df_meteo.to_csv(index=False)
        print("✅ Dati Meteo ricevuti.\n")

        if 'current' in data:
            temp_attuale = data['current']['temperature_2m']
            umidita_attuale = data['current']['relative_humidity_2m']
            # Logica semplice per lo stato
            if temp_attuale > 30 or data['daily']['wind_speed_10m_max'][0] > 40:
                condizione_frontend = "ALLERTA"

    except Exception as e:
        print(f"❌ Errore API: {e}")
        return {"errore": str(e)}

    print(f"🤖 Configurazione AI per profilo: {TIPO_PROFILO}...")
    client = Groq(api_key=API_KEY)

    if TIPO_PROFILO == "ORGANIZZAZIONE":
        descrizione_ruolo = "Sei un Analista Meteo per la gestione delle risorse ospedaliere."
        target = "Personale amministrativo e sanitario."
        focus_ordini = "Pianificazione turni, verifica infrastrutture, gestione comfort ambientale pazienti."
    else:
        descrizione_ruolo = "Sei un Assistente Personale per il meteo e la sicurezza quotidiana."
        target = "Cittadini e famiglie."
        focus_ordini = "Consigli su abbigliamento, attività all'aperto, prudenza alla guida, comfort in casa."

    # --- MODIFICA CRUCIALE: INSERITO ESEMPIO VISIVO ---
    prompt_sicurezza = f"""
    RUOLO: {descrizione_ruolo}
    TARGET: {target}
    TONO: Professionale, Calmo, Diretto.

    DATI DA ANALIZZARE:
    1. STORICO: {csv_storico}
    2. PREVISIONI: {csv_futuro}
    3. FOCUS CONSIGLI: {focus_ordini}

    COMPITO:
    Genera il report meteo per i prossimi 3 giorni.

    ⛔ REGOLE TASSATIVE (VIETATO SBAGLIARE):
    1. NON scrivere frasi introduttive (es. "Ecco le raccomandazioni", "Analisi meteo").
    2. NON ripetere la parola "UTENTE".
    3. Inizia SUBITO col formato sottostante.

    --- ESEMPIO DI OUTPUT PERFETTO (COPIA QUESTO STILE) ---

    [DATA: 2024-05-20]
    --------------------------------------------------
    🌤️ SITUAZIONE: 22.5°C | Vento 12 km/h | Pioggia 0.0 mm
    📊 LIVELLO ATTENZIONE: Basso
    ℹ️ NOTE METEO: Cielo sereno e temperature gradevoli.

    💡 CONSIGLI PRATICI:
    1. Indossa occhiali da sole e protezione solare leggera.
    2. Ideale per attività all'aperto o passeggiate.
    3. Nessun rischio per la guida.
    --------------------------------------------------

    (Ora genera il report reale seguendo ESATTAMENTE l'esempio sopra per i giorni richiesti).
    """

    ai_response_text = "Errore AI"

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Sei un generatore di report. Non chattare. Non salutare. Genera solo i dati formattati."},
                {"role": "user", "content": prompt_sicurezza}
            ],
            temperature=0.1, 
        )

        print("\n" + f"📋 BOLLETTINO METEO: {TIPO_PROFILO} 📋".center(60, "="))
        ai_response_text = completion.choices[0].message.content
        print(ai_response_text) # Stampa in console server come volevi
        print("="*60)

    except Exception as e:
        print(f"❌ ERRORE AI: {e}")
        ai_response_text = f"Errore generazione AI: {e}"

    # --- 5. PREPARAZIONE PACCHETTO DATI PER HTML (JSON) ---
    # Qui impacchettiamo tutto ciò che hai calcolato per mandarlo al sito
    
    # Generazione dati simulati per grafico e mappa (perché l'API meteo non li da specifici per quartiere)
    pressione_ospedaliera = [random.randint(30, 80) for _ in range(6)]
    
    payload_finale = {
        "meteo": {
            "temp": temp_attuale,
            "umidita": umidita_attuale,
            "citta": "Napoli",
            "condizione": condizione_frontend
        },
        "ia_advice": ai_response_text, # Qui inseriamo il testo generato dal tuo prompt originale
        "grafico_ospedali": {
            "orari": ["08:00", "12:00", "16:00", "20:00", "00:00", "04:00"],
            "valori": pressione_ospedaliera
        },
        "mappa": [
            {"nome": "Centro Storico", "lat": 40.8518, "lng": 14.2681, "valore": temp_attuale + 1, "rischio": "alto" if temp_attuale > 30 else "medio"},
            {"nome": "Vomero", "lat": 40.8440, "lng": 14.2290, "valore": temp_attuale - 2, "rischio": "basso"}
        ]
    }

    # --- SALVATAGGIO IN CACHE ---
    CACHE_DATI = payload_finale
    LAST_CALL = time.time()
    
    return payload_finale

# --- AVVIO DEL SERVER ---
if __name__ == "__main__":
    print("🚀 Avvio Server AI Meteo...")
    # Lancia il server sulla porta 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)