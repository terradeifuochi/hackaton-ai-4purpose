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
        labels: [], // Si riempirà coi dati Python
        datasets: [{
            label: 'Temp. Prevista (°C)',
            data: [], // Si riempirà coi dati Python
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

// 4. Funzione Principale di Collegamento al Server
async function scaricaDatiDaPython() {
    console.log("🚀 Richiedo dati aggiornati al server Python...");
    
    try {
        // Chiamata al server locale
        const response = await fetch('http://127.0.0.1:8000/api/dati');
        
        if (!response.ok) {
            throw new Error(`Errore Server: ${response.status}`);
        }

        const data = await response.json();
        console.log("📦 Dati ricevuti:", data);

        // --- A. AGGIORNAMENTO DATI LIVE ---
        // Nota: uso 'data.live' perché così l'abbiamo chiamato in Python
        document.getElementById('temp-val').innerText = data.live.temp + "°C";
        document.getElementById('hum-val').innerText = data.live.umidita + "%";
        
        // Verifica se l'elemento vento esiste nell'HTML prima di aggiornarlo
        const windEl = document.getElementById('wind-val');
        if(windEl) windEl.innerText = data.live.vento + " km/h";
        
        // --- B. AGGIORNAMENTO TESTO AI ---
        document.getElementById('ai-text').innerText = '"' + data.ia_advice + '"';

        // --- C. AGGIORNAMENTO MAPPA ---
        // Rimuove i vecchi cerchi
        map.eachLayer((layer) => {
            if (layer instanceof L.Circle) { map.removeLayer(layer); }
        });

        // Aggiunge i nuovi cerchi dalle coordinate Python
        data.mappa.forEach(zona => {
            const color = zona.rischio === 'alto' ? '#ef4444' : '#f59e0b'; // Rosso o Arancio
            L.circle([zona.lat, zona.lng], {
                color: color, 
                fillColor: color, 
                fillOpacity: 0.5, 
                radius: 1500
            }).addTo(map)
            .bindPopup(`<b>${zona.nome}</b><br>Temp: ${zona.valore}°C<br>Rischio: ${zona.rischio.toUpperCase()}`);
        });

        // --- D. AGGIORNAMENTO CARD PREVISIONI 48H ---
        const forecastContainer = document.getElementById('forecast-container');
        forecastContainer.innerHTML = ''; // Pulisce le card vecchie
        
        data.previsioni_48h.forEach(prev => {
            // Logica colori: se > 30 gradi diventa rossa
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
        
        // Ricarica le icone dentro le nuove card
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

// 5. Avvio
scaricaDatiDaPython();


setInterval(scaricaDatiDaPython, 180000);