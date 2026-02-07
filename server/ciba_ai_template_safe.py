import os
import requests
import pandas as pd
from datetime import date, timedelta
from groq import Groq 

# --- 1. CONFIGURAZIONE ---
# ⚠️ IMPORTANTE: Inserisci qui la tua chiave. Per sicurezza non lasciarla nel codice se lo condividi.
API_KEY = "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" 

# Coordinate (Napoli)
LAT = 40.8518
LON = 14.2681

# --- 2. RECUPERO DATI ESTESO (include VENTO e TEMP. PERCEPITA) ---
oggi = date.today()
sette_giorni_fa = oggi - timedelta(days=7)
dopodomani = oggi + timedelta(days=2) 

str_oggi = oggi.strftime("%Y-%m-%d")
str_inizio = sette_giorni_fa.strftime("%Y-%m-%d")
str_fine_previsione = dopodomani.strftime("%Y-%m-%d")

print(f"📡 Scarico dati Meteo Completi (Temp, Vento, Pioggia)...")

try:
    # AGGIUNTA PARAMETRI: wind_speed_10m_max (Vento) e apparent_temperature_max (Temp Percepita/Afa)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&start_date={str_inizio}&end_date={str_fine_previsione}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,apparent_temperature_max&timezone=Europe%2FBerlin"
    
    r = requests.get(url, timeout=10)
    data = r.json()
    
    # Creazione DataFrame con tutti i parametri
    df = pd.DataFrame({
        'Data': pd.to_datetime(data['daily']['time']), 
        'T_Reale_Max': data['daily']['temperature_2m_max'],
        'T_Percepita_Max': data['daily']['apparent_temperature_max'], # Fondamentale per il calore
        'Pioggia_mm': data['daily']['precipitation_sum'],
        'Vento_Max_kmh': data['daily']['wind_speed_10m_max'] # Fondamentale per i danni
    })

    ts_oggi = pd.to_datetime(oggi)

    # Preparazione dati per l'AI
    dati_oggi = df[df['Data'] == ts_oggi].iloc[0]
    
    # Filtriamo solo da oggi in poi per l'analisi predittiva
    df_futuro = df[df['Data'] >= ts_oggi]
    csv_futuro = df_futuro.to_csv(index=False)
    
    # Tutto il contesto
    csv_completo = df.to_csv(index=False)

    print("✅ Dati ricevuti correttamente.\n")

except Exception as e:
    print(f"❌ Errore scaricamento dati: {e}")
    exit()

# --- 3. ANALISI PREDITTIVA DISASTRI (AI) ---
print("🤖 L'Intelligenza Artificiale sta calcolando i rischi di disastri...")

client = Groq(api_key=API_KEY)

# --- PROMPT INGEGNERIZZATO PER RILEVAZIONE DISASTRI ---
prompt_sicurezza = f"""
Sei un'Intelligenza Artificiale avanzata per la PREVENZIONE DEI DISASTRI METEOROLOGICI a Napoli.

ANALIZZA I SEGUENTI DATI METEO (Oggi + Prossime 48h):
{csv_futuro}

COMPITO:
Analizza combinazioni di Calore, Vento e Pioggia per prevedere pericoli PRIMA che accadano.

REGOLE DI VALUTAZIONE RISCHIO (SOGLIE):
1. CALORE ESTREMO: Se 'T_Percepita_Max' > 35°C -> RISCHIO SALUTE (Colpo di calore).
2. TEMPESTA DI VENTO: Se 'Vento_Max_kmh' > 60 km/h -> RISCHIO CADUTA ALBERI/CORNICIONI.
3. ALLUVIONE LAMPO: Se 'Pioggia_mm' > 30mm in 24h -> RISCHIO ALLAGAMENTI.
4. URAGANO MEDITERRANEO: Se Vento > 80 km/h + Pioggia > 40mm -> DISASTRO IMMINENTE.

OUTPUT RICHIESTO (Formatta esattamente così):

1. 🛑 STATO DI ALLERTA ATTUALE ({str_oggi}):
   - LIVELLO: [VERDE / GIALLO / ARANCIONE / ROSSO]
   - MINACCIA PRINCIPALE: [Es. Calore estremo, Vento forte, Ecc.]
   - CONSIGLIO IMPERATIVO: [Es. "NON USCIRE DI CASA", "BEVI MOLTA ACQUA", "GUIDA CON PRUDENZA"]

2. 🔮 PREVISIONI TATTICHE (Prossimi 2 Giorni):
   Per ogni giorno (Domani e Dopodomani) scrivi:
   - [DATA]: [Descrizione sintetica] 
     (Temp. Percepita: X°C | Vento: Y km/h | Pioggia: Z mm)
     -> RISCHIO: [BASSO/MEDIO/ALTO/ESTREMO]
     -> AZIONE CONSIGLIATA: [Cosa fare per salvarsi/proteggersi]

3. ⚠️ ANALISI DISASTRI POTENZIALI:
   Se rilevi una combinazione pericolosa nei dati futuri, scrivi un paragrafo di avvertimento preventivo. Esempio: "Attenzione: Il vento forte combinato al terreno secco potrebbe causare incendi" oppure "Attenzione: La pioggia forte su terreno caldo creerà effetto serra e allagamenti".
   Se non ci sono rischi gravi, scrivi "Nessuna configurazione disastrosa rilevata."
"""

try:
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Sei il sistema di allerta della Protezione Civile. Sii diretto, autoritario e preoccupati della sicurezza umana."},
            {"role": "user", "content": prompt_sicurezza}
        ],
        temperature=0.1, 
    )

    print("\n" + "🚨 REPORT PREVENZIONE DISASTRI 🚨".center(60, "="))
    print(completion.choices[0].message.content)
    print("="*60)

except Exception as e:
    print(f"❌ ERRORE AI: {e}")