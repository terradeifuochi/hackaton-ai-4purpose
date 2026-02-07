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
        const response = await fetch('http://127.0.0.1:8000/api/dati');
        if (!response.ok) throw new Error(`Errore Server: ${response.status}`);
        const data = await response.json();
        console.log("📦 Dati ricevuti:", data);

        // --- A. DATI LIVE ---
        document.getElementById('temp-val').innerText = data.live.temp + "°C";
        document.getElementById('hum-val').innerText = data.live.umidita + "%";
        
        const windEl = document.getElementById('wind-val');
        if(windEl) windEl.innerText = data.live.vento + " km/h";

        const rainEl = document.getElementById('rain-val');
        if(rainEl) rainEl.innerText = data.live.pioggia_prob + "%";
        
        document.getElementById('ai-text').innerText = '"' + data.ia_advice + '"';

        // --- B. MAPPA ---
        map.eachLayer((layer) => { if (layer instanceof L.Circle) map.removeLayer(layer); });

        data.mappa.forEach(zona => {
            let color = '#22c55e'; // Verde
            let description = "Situazione stabile.";
            const rischioLower = zona.rischio.toLowerCase();

            if (rischioLower.includes('rosso')) { color = '#ef4444'; description = "PERICOLO: Critico."; } 
            else if (rischioLower.includes('arancione')) { color = '#f97316'; description = "ATTENZIONE: Intenso."; }
            else if (rischioLower.includes('giallo')) { color = '#eab308'; description = "PREALLERTA."; }

            const circle = L.circle([zona.lat, zona.lng], {
                color: color, fillColor: color, fillOpacity: 0.6, radius: 1500
            }).addTo(map);

            circle.bindTooltip(`
                <div style="text-align: center; color: #1e293b;">
                    <strong style="font-size: 14px; color: ${color}">${zona.nome}</strong><br>
                    <span style="font-weight:bold; font-size:10px;">${description}</span>
                </div>
            `, { permanent: false, direction: 'top', className: 'custom-tooltip', opacity: 0.95 });
        });

        // --- C. AGGIORNAMENTO CARD PREVISIONI 48H (CON DETTAGLI) ---
        const forecastContainer = document.getElementById('forecast-container');
        forecastContainer.innerHTML = ''; 
        
        data.previsioni_48h.forEach(prev => {
            let isHot = prev.temp >= 30;
            let borderClass = isHot ? 'border-red-500 bg-red-500/10' : 'border-slate-700 bg-slate-800';
            let iconColor = isHot ? 'text-red-500' : 'text-yellow-400';

            // Nuova struttura HTML per la card con dettagli
            const html = `
                <div class="${borderClass} border p-3 rounded-xl flex flex-col items-center gap-2 text-center w-full">
                    <div class="w-full flex justify-between items-center border-b border-slate-700 pb-1 mb-1">
                        <span class="text-slate-400 text-[10px] font-bold uppercase">${prev.giorno}</span>
                        <span class="text-white text-xs font-bold">${prev.ora}</span>
                    </div>

                    <div class="flex items-center gap-2">
                        <i data-lucide="${prev.icona}" class="${iconColor} w-8 h-8"></i>
                        <span class="text-2xl font-black text-white">${prev.temp}°</span>
                    </div>

                    <div class="grid grid-cols-3 gap-2 w-full mt-1 bg-slate-900/50 p-1 rounded-lg">
                        <div class="flex flex-col items-center" title="Prob. Pioggia">
                            <i data-lucide="cloud-rain" class="w-3 h-3 text-cyan-400 mb-1"></i>
                            <span class="text-[10px] text-cyan-200 font-bold">${prev.pioggia}%</span>
                        </div>
                        <div class="flex flex-col items-center" title="Vento">
                            <i data-lucide="wind" class="w-3 h-3 text-emerald-400 mb-1"></i>
                            <span class="text-[10px] text-emerald-200 font-bold">${Math.round(prev.vento)}</span>
                        </div>
                        <div class="flex flex-col items-center" title="Umidità">
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
        myChart.data.labels = data.grafico.orari;
        myChart.data.datasets[0].data = data.grafico.valori;
        myChart.update();

    } catch (error) {
        console.log("❌ ERRORE:", error);
        document.getElementById('ai-text').innerText = "⚠️ Server Offline";
        document.getElementById('ai-text').classList.add("text-red-500");
    }
}

// Avvio
scaricaDatiDaPython();
setInterval(scaricaDatiDaPython, 300000);