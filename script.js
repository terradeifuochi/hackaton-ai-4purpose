// 1. Inizializza le icone al caricamento
lucide.createIcons();

// 2. Configurazione Mappa (Leaflet)
const map = L.map('map').setView([40.8518, 14.2681], 11);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '© OpenStreetMap, © CartoDB'
}).addTo(map);

// 3. Configurazione Grafico
const ctx = document.getElementById('hospitalChart').getContext('2d');
let myChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Temp. Prevista (°C)',
            data: [],
            borderColor: '#a855f7',
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
            y: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
            x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
        }
    }
});

// 4. Funzione Principale
async function scaricaDatiDaPython() {
    console.log("🚀 Richiedo dati aggiornati...");
    
    try {
        // Aggiungiamo un timestamp alla fine dell'URL per "ingannare" la cache
        const response = await fetch(`http://127.0.0.1:8000/api/dati?t=${new Date().getTime()}`);        
        if (!response.ok) throw new Error(`Errore Server: ${response.status}`);
        
        const data = await response.json();
        
        // Gestione errore specifico dal Backend (es. CSV non trovato)
        if (data.error) {
            console.error("⚠️ Errore dal server Python:", data.error);
            const aiEl = document.getElementById('ai-text');
            aiEl.innerText = "ERRORE DATI: " + data.error;
            aiEl.style.color = "#ef4444"; 
            return; 
        }
        
        console.log("📦 Dati ricevuti:", data);

        // --- A. DATI LIVE & COLORI DINAMICI ---
        const allerta = data.live.allerta.toLowerCase();
        const tempEl = document.getElementById('temp-val');
        
        // Reset classi colore temperatura
        tempEl.className = "text-5xl font-black mt-1"; 
        
        if (allerta.includes('ross')) {
            tempEl.classList.add("text-red-500", "animate-pulse");
        } else if (allerta.includes('aranc')) {
            tempEl.classList.add("text-orange-500");
        } else if (allerta.includes('giall')) {
            tempEl.classList.add("text-yellow-400");
        } else {
            tempEl.classList.add("text-green-500");
        }

        tempEl.innerText = data.live.temp + "°C";
        document.getElementById('hum-val').innerText = data.live.umidita + "%";
        
        const windEl = document.getElementById('wind-val');
        if(windEl) windEl.innerText = data.live.vento + " km/h";

        const rainEl = document.getElementById('rain-val');
        if(rainEl) rainEl.innerText = data.live.pioggia_prob + "%";
        
        const aiTextEl = document.getElementById('ai-text');
        aiTextEl.innerText = '"' + data.ia_advice + '"';
        aiTextEl.style.color = ""; // Reset colore errore

        // --- B. MAPPA (PALLINO DINAMICO) ---
        map.eachLayer((layer) => { if (layer instanceof L.Circle) map.removeLayer(layer); });

        data.mappa.forEach(zona => {
            let color = '#22c55e'; // Verde
            let description = "Situazione stabile.";
            let radius = 1500;

            if (allerta.includes('ross')) { 
                color = '#ef4444'; 
                description = "PERICOLO: Critico."; 
                radius = 2500; 
            } else if (allerta.includes('aranc')) { 
                color = '#f97316'; 
                description = "ATTENZIONE: Intenso."; 
                radius = 2000;
            } else if (allerta.includes('giall')) { 
                color = '#eab308'; 
                description = "PREALLERTA."; 
                radius = 1800;
            }

            const circle = L.circle([zona.lat, zona.lng], {
                color: color, 
                fillColor: color, 
                fillOpacity: 0.6, 
                radius: radius,
                weight: 2
            }).addTo(map);

            // Animazione pulse per allerta alta
            if (allerta.includes('ross') || allerta.includes('aranc')) {
                const el = circle.getElement();
                if(el) el.classList.add('animate-pulse');
            }

            circle.bindTooltip(`
                <div style="text-align: center; color: #1e293b;">
                    <strong style="font-size: 14px; color: ${color}">${zona.nome}</strong><br>
                    <span style="font-weight:bold; font-size:10px;">${description}</span><br>
                    <span style="font-size:10px;">Rilevato: ${data.live.temp}°C</span>
                </div>
            `, { permanent: false, direction: 'top', className: 'custom-tooltip', opacity: 0.95 });
        });

        // --- C. AGGIORNAMENTO CARD PREVISIONI 48H (LOGICA LAVA) ---
        const forecastContainer = document.getElementById('forecast-container');
        forecastContainer.innerHTML = ''; 

        data.previsioni_48h.forEach(prev => {
            const isLava = prev.temp >= 35 || prev.vento >= 40; 
            const isHot = prev.temp >= 30;

            let borderClass = "";
            let iconColor = "";

            if (isLava) {
                borderClass = 'border-red-500 bg-gradient-to-br from-red-900 via-red-950 to-black shadow-[0_0_15px_rgba(239,68,68,0.5)] animate-pulse';
                iconColor = 'text-orange-500';
            } else if (isHot) {
                borderClass = 'border-red-500 bg-red-500/10';
                iconColor = 'text-red-500';
            } else {
                borderClass = 'border-slate-700 bg-slate-800';
                iconColor = 'text-yellow-400';
            }

            const html = `
                <div class="${borderClass} border p-3 rounded-xl flex flex-col items-center gap-2 text-center w-full transition-all duration-500">
                    <div class="w-full flex justify-between items-center border-b border-slate-700 pb-1 mb-1">
                        <span class="text-slate-400 text-[10px] font-bold uppercase">${prev.giorno}</span>
                        <span class="text-white text-xs font-bold">${prev.ora}</span>
                    </div>

                    <div class="flex items-center gap-2">
                        <i data-lucide="${isLava ? 'flame' : prev.icona}" class="${iconColor} w-8 h-8"></i>
                        <span class="text-2xl font-black text-white">${prev.temp}°</span>
                    </div>

                    <div class="grid grid-cols-3 gap-2 w-full mt-1 bg-black/40 p-1 rounded-lg">
                        <div class="flex flex-col items-center">
                            <i data-lucide="cloud-rain" class="w-3 h-3 text-cyan-400 mb-1"></i>
                            <span class="text-[10px] text-cyan-200 font-bold">${prev.pioggia}%</span>
                        </div>
                        <div class="flex flex-col items-center">
                            <i data-lucide="wind" class="w-3 h-3 ${prev.vento >= 40 ? 'text-red-500 animate-bounce' : 'text-emerald-400'} mb-1"></i>
                            <span class="text-[10px] ${prev.vento >= 40 ? 'text-red-400' : 'text-emerald-200'} font-bold">${Math.round(prev.vento)}</span>
                        </div>
                        <div class="flex flex-col items-center">
                            <i data-lucide="droplets" class="w-3 h-3 text-blue-400 mb-1"></i>
                            <span class="text-[10px] text-blue-200 font-bold">${prev.umidita}%</span>
                        </div>
                    </div>
                </div>
            `;
            forecastContainer.innerHTML += html;
        });

        lucide.createIcons();

        // --- D. GRAFICO ---
// --- D. GRAFICO ---
// ERRORE PRECEDENTE: myChart.datasets[0].data (mancava .data prima di datasets)
        myChart.data.labels = data.grafico.orari;
        myChart.data.datasets[0].data = data.grafico.valori; // Corretto: aggiunto .data.
        myChart.update();

    } catch (error) {
        console.error("❌ ERRORE CONNESSIONE:", error);
        const aiEl = document.getElementById('ai-text');
        aiEl.innerText = "⚠️ Server Offline - Verifica che il backend sia attivo";
        aiEl.classList.add("text-red-500");
    }
}

// Avvio e aggiornamento ogni 30 secondi
scaricaDatiDaPython();
setInterval(scaricaDatiDaPython, 30000);