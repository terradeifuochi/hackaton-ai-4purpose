import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys

# --- 1. IMPOSTAZIONI ---
LAT = 40.8518   # Napoli
LON = 14.2681
CITTA = "Napoli"
START = "2014-01-01"
END = "2024-02-08"

print(f"📡 SCARICO I DATI VERI PER {CITTA}...")

# --- 2. SCARICAMENTO ---
url = f"https://archive-api.open-meteo.com/v1/archive?latitude={LAT}&longitude={LON}&start_date={START}&end_date={END}&daily=temperature_2m_max&timezone=Europe%2FBerlin"

try:
    r = requests.get(url)
    data = r.json()
    if "error" in data:
        print("Errore API:", data['reason'])
        sys.exit()
except Exception as e:
    print("Errore connessione:", e)
    sys.exit()

# --- 3. CREAZIONE DATI ---
df = pd.DataFrame({
    'Data': pd.to_datetime(data['daily']['time']),
    'Tmax': data['daily']['temperature_2m_max']
})
df.set_index('Data', inplace=True)

# Record Assoluto
picco_assoluto_val = df['Tmax'].max()
picco_assoluto_data = df['Tmax'].idxmax()

print(f"✅ TROVATI {len(df)} GIORNI DI DATI")
print(f"🔥 RECORD ASSOLUTO: {picco_assoluto_val}°C il {picco_assoluto_data.strftime('%d/%m/%Y')}")

# --- 4. ANALISI ONDATE ---
SOGLIA = 34.0
ondate = []
temp_consecutivi = 0
inizio = None

for data, row in df.iterrows():
    temp = row['Tmax']
    if temp >= SOGLIA:
        if temp_consecutivi == 0:
            inizio = data
        temp_consecutivi += 1
    else:
        if temp_consecutivi >= 3:
            fine = data - pd.Timedelta(days=1)
            subset = df.loc[inizio:fine]
            max_val = subset['Tmax'].max()
            data_picco = subset['Tmax'].idxmax()
            
            ondate.append({
                'Inizio': inizio, 
                'Fine': fine, 
                'Giorni': temp_consecutivi,
                'Picco_Valore': max_val,
                'Picco_Data': data_picco
            })
        temp_consecutivi = 0

df_ondate = pd.DataFrame(ondate)

# --- 5. GRAFICO CLEAN & STRAIGHT ---
print(f"🔥 Trovate {len(df_ondate)} ondate di calore.")
print("Generazione grafico orizzontale pulito...")

fig, ax = plt.subplots(figsize=(16, 9)) 

# Aumentiamo lo spazio sotto per farci stare le due righe di testo
plt.subplots_adjust(bottom=0.2) 

# Linea temperatura
ax.plot(df.index, df['Tmax'], color='cornflowerblue', linewidth=0.8, label='Temperatura Giornaliera')
ax.axhline(SOGLIA, color='red', linestyle='--', linewidth=1, label=f'Soglia {SOGLIA}°C')

if not df_ondate.empty:
    # Usiamo enumerate per alternare (0, 1, 2...)
    for i, (_, row) in enumerate(df_ondate.iterrows()):
        # Fascia rossa
        ax.axvspan(row['Inizio'], row['Fine'], color='red', alpha=0.2)
        
        # --- TESTO DRITTO SOTTO L'ASSE X ---
        label_text = f"{row['Picco_Data'].strftime('%b %y')}\n{row['Picco_Valore']}°"
        
        # Logica alternata: 
        # I pari (0, 2, 4...) vanno nella riga superiore (vicino all'asse)
        # I dispari (1, 3, 5...) vanno nella riga inferiore (più giù)
        offset_y = -0.08 if i % 2 == 0 else -0.16
        
        ax.text(row['Picco_Data'], offset_y, 
                label_text, 
                transform=ax.get_xaxis_transform(), # Coordinate relative all'asse
                fontsize=9, 
                rotation=0,       # DRITTO!
                ha='center', 
                va='top', 
                color='black',    # Nero per massima leggibilità
                fontweight='bold' if row['Picco_Valore'] > 37 else 'normal') # Grassetto se > 37°
        
        # Puntino rosso sulla curva
        ax.scatter(row['Picco_Data'], row['Picco_Valore'], color='red', s=15, zorder=5)
        
        # Lineetta grigia che collega il testo all'asse (opzionale, ma aiuta la lettura)
        if i % 2 != 0: # Solo per quelli più in basso
             ax.plot([row['Picco_Data'], row['Picco_Data']], [SOGLIA-2, SOGLIA-5], 
                     color='gray', linestyle=':', alpha=0.3, transform=ax.transData)


# --- EVIDENZIAMO IL RE (RECORD ASSOLUTO) ---
ax.scatter(picco_assoluto_data, picco_assoluto_val, color='gold', s=150, edgecolors='black', zorder=10, label='Record Assoluto')
ax.annotate(f"RECORD: {picco_assoluto_val}°\n{picco_assoluto_data.strftime('%d %b %Y')}", 
            xy=(picco_assoluto_data, picco_assoluto_val), 
            xytext=(picco_assoluto_data, picco_assoluto_val + 2.5),
            arrowprops=dict(facecolor='black', arrowstyle='->'),
            fontsize=10, fontweight='bold', ha='center',
            bbox=dict(boxstyle="square,pad=0.3", fc="white", ec="black", alpha=0.9))

# Formattazione Asse
ax.set_ylim(bottom=10) 
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax.grid(True, linestyle='-', alpha=0.2) # Griglia leggerissima

plt.title(f'Analisi Ondate di Calore: {CITTA} (2014-2024)', fontsize=18, pad=20)
plt.ylabel('Temperatura (°C)')
plt.legend(loc='upper left')

# SALVA
nome_file = "grafico_napoli_horizontal_clean.png"
plt.savefig(nome_file, dpi=150)
print(f"✅ FATTO! Apri '{nome_file}'. Le scritte sono dritte e non si toccano!")