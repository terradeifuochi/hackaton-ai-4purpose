// 1. Inizializza le icone al caricamento
lucide.createIcons();

// 2. Configurazione Mappa (Leaflet)
const map = L.map('map').setView([40.8518, 14.2681], 11); // Zoom su Napoli
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '© OpenStreetMap, © CartoDB'
}).addTo(map);

// 3. Configurazione Grafico (Chart.js)
const ctx = document.getElementById('hospitalChart').getContext('2d');
let myChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Temp. Prevista (°C)',
            data: [],
            borderColor: '#a855f7', // Viola AIDA
            backgroundColor: 'rgba(168, 85, 247, 0.2)',
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            pointRadius: 4,
            pointBackgroundColor: '#fff'
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            y: { 
                grid: { color: '#334155' }, 
                ticks: { color: '#94a3b8' } 
            },
            x: { 
                grid: { display: false }, 
                ticks: { color: '#94a3b8' } 
            }
        }
    }
});

// 4. Funzione Principale
async function scaricaDatiDaPython() {
    console.log("🚀 Richiedo dati aggiornati al server Python...");
    
    try {
        const response = await fetch('http://127.0.0.1:8000/api/dati');
        
        if (!response.ok) {
            throw new Error(`Errore Server: ${response.status}`);
        }

        const data = await response.json();
        console.log("📦 Dati ricevuti:", data);

        // --- A. AGGIORNAMENTO DATI LIVE ---
        document.getElementById('temp-val').innerText = data.live.temp + "°C";
        document.getElementById('hum-val').innerText = data.live.umidita + "%";
        
        const windEl = document.getElementById('wind-val');
        if(windEl) windEl.innerText = data.live.vento + " km/h";

        // Probabilità Pioggia (Nuovo)
        const rainEl = document.getElementById('rain-val');
        if(rainEl) rainEl.innerText = data.live.pioggia_prob + "%";
        
        // --- B. AGGIORNAMENTO TESTO AI ---
        document.getElementById('ai-text').innerText = '"' + data.ia_advice + '"';

        // --- C. AGGIORNAMENTO MAPPA (COLORI E HOVER) ---
        
        // Rimuove i vecchi cerchi
        map.eachLayer((layer) => {
            if (layer instanceof L.Circle) { map.removeLayer(layer); }
        });

        // Genera i nuovi cerchi
        data.mappa.forEach(zona => {
            
            // 1. Logica Colori Avanzata
            let color = '#22c55e'; // Default: VERDE (Sicuro)
            let description = "Situazione stabile. Nessun rischio rilevato."; // Default descrizione
            
            const rischioLower = zona.rischio.toLowerCase();

            if (rischioLower.includes('rosso') || rischioLower.includes('alto')) {
                color = '#ef4444'; // Rosso
                description = `PERICOLO: Temperature critiche (${zona.valore}°C). Rischio colpi di calore.`;
            } 
            else if (rischioLower.includes('arancione') || rischioLower.includes('medio')) {
                color = '#f97316'; // Arancione
                description = `ATTENZIONE: Calore intenso (${zona.valore}°C). Limitare esposizione.`;
            }
            else if (rischioLower.includes('giallo') || rischioLower.includes('gialla')) {
                color = '#eab308'; // Giallo
                description = `PREALLERTA: Temperature in aumento.`;
            }
            else if (rischioLower.includes('blu')) {
                color = '#3b82f6'; // Blu
                description = `FREDDO/PIOGGIA: Temperatura bassa o precipitazioni in corso.`;
            }
            else {
                // Rimane Verde
                color = '#22c55e';
                description = `SICUREZZA: Parametri nella norma (${zona.valore}°C).`;
            }

            // 2. Creazione Cerchio
            const circle = L.circle([zona.lat, zona.lng], {
                color: color, 
                fillColor: color, 
                fillOpacity: 0.6, 
                radius: 1500
            }).addTo(map);

            // 3. TOOLTIP AL PASSAGGIO DEL MOUSE (Hover)
            circle.bindTooltip(`
                <div style="text-align: center; color: #1e293b;">
                    <strong style="font-size: 14px; color: ${color}">${zona.nome}</strong><br>
                    <span style="font-weight:bold; font-size:10px; text-transform:uppercase;">STATUS: ${zona.rischio}</span><br>
                    <span style="font-size: 11px;">${description}</span>
                </div>
            `, {
                permanent: false, // Appare solo al passaggio del mouse
                direction: 'top',
                className: 'custom-tooltip', // Classe CSS opzionale
                opacity: 0.95
            });
        });

        // --- D. AGGIORNAMENTO CARD PREVISIONI 48H ---
        const forecastContainer = document.getElementById('forecast-container');
        forecastContainer.innerHTML = ''; 
        
        data.previsioni_48h.forEach(prev => {
            let isHot = prev.temp >= 30;
            let borderClass = isHot ? 'border-red-500 bg-red-500/10' : 'border-slate-700 bg-slate-800';
            let iconColor = isHot ? 'text-red-500' : 'text-yellow-400';

            const html = `
                <div class="${borderClass} border p-3 rounded-xl flex flex-col items-center gap-1 text-center min-w-[90px]">
                    <span class="text-slate-400 text-[10px] font-bold uppercase">${prev.giorno}</span>
                    <span class="text-white text-xs font-bold">${prev.ora}</span>
                    <i data-lucide="${prev.icona}" class="${iconColor} w-6 h-6 my-1"></i>
                    <span class="text-xl font-black text-white">${prev.temp}°</span>
                </div>
            `;
            forecastContainer.innerHTML += html;
        });
        
        lucide.createIcons();

        // --- E. AGGIORNAMENTO GRAFICO ---
        myChart.data.labels = data.grafico.orari;
        myChart.data.datasets[0].data = data.grafico.valori;
        myChart.update();

    } catch (error) {
        console.error("❌ ERRORE CONNESSIONE:", error);
        document.getElementById('ai-text').innerText = "⚠️ Server Offline: Assicurati che Python sia avviato!";
        document.getElementById('ai-text').classList.add("text-red-500");
    }
}

// 5. Avvio e Aggiornamento
scaricaDatiDaPython();
    setInterval(scaricaDatiDaPython, 180000); // 3 Minuti