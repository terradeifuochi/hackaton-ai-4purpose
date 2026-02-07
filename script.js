lucide.createIcons();

const map = L.map('map').setView([40.8518, 14.2681], 12);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '© OpenStreetMap'
}).addTo(map);

const ctx = document.getElementById('hospitalChart').getContext('2d');
let myChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Temperatura Prevista (°C)',
            data: [],
            borderColor: '#f97316', // Arancione per temperatura
            backgroundColor: 'rgba(249, 115, 22, 0.1)',
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            pointRadius: 4
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            y: { grid: { color: '#334155' } },
            x: { grid: { display: false } }
        }
    }
});

async function scaricaDatiDaPython() {
    try {
        const response = await fetch('http://127.0.0.1:8000/api/dati');
        const data = await response.json();

        // 1. Live Data
        document.getElementById('temp-val').innerText = data.live.temp + "°C";
        document.getElementById('hum-val').innerText = data.live.umidita + "%";
        document.getElementById('wind-val').innerText = data.live.vento + " km/h";
        
        // 2. AI Text (Ora in alto)
        document.getElementById('ai-text').innerText = '"' + data.ia_advice + '"';

        // 3. Mappa
        map.eachLayer((layer) => {
            if (layer instanceof L.Circle) { map.removeLayer(layer); }
        });

        data.mappa.forEach(zona => {
            const color = zona.rischio === 'alto' ? '#ef4444' : '#f59e0b';
            L.circle([zona.lat, zona.lng], {
                color: color, fillColor: color, fillOpacity: 0.5, radius: 1200
            }).addTo(map);
        });

        // 4. Previsioni 48h (Card)
        const forecastContainer = document.getElementById('forecast-container');
        forecastContainer.innerHTML = '';
        
        data.previsioni_48h.forEach(prev => {
            let isHot = prev.temp >= 40;
            let borderClass = isHot ? 'border-red-500 bg-red-500/10' : 'border-slate-700 bg-slate-800';
            let iconColor = isHot ? 'text-red-500' : 'text-yellow-400';

            const html = `
                <div class="${borderClass} border p-3 rounded-xl flex flex-col items-center gap-1 text-center">
                    <span class="text-slate-400 text-[10px] font-bold uppercase">${prev.giorno}</span>
                    <span class="text-white text-xs font-bold">${prev.ora}</span>
                    <i data-lucide="${prev.icona}" class="${iconColor} w-6 h-6 my-1"></i>
                    <span class="text-xl font-black text-white">${prev.temp}°</span>
                </div>
            `;
            forecastContainer.innerHTML += html;
        });
        lucide.createIcons();

        // 5. Aggiorna Grafico
        myChart.data.labels = data.grafico.orari;
        myChart.data.datasets[0].data = data.grafico.valori;
        myChart.update();

    } catch (error) {
        console.error(error);
    }
}

scaricaDatiDaPython();
setInterval(scaricaDatiDaPython, 180000);