lucide.createIcons();

const map = L.map('map').setView([40.8518, 14.2681], 12);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '© OpenStreetMap, © CartoDB'
}).addTo(map);

const ctx = document.getElementById('hospitalChart').getContext('2d');
let myChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Pressione Ospedaliera Prevista',
            data: [],
            borderColor: '#f97316',
            backgroundColor: 'rgba(249, 115, 22, 0.2)',
            borderWidth: 3,
            fill: true,
            tension: 0.4
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

        document.getElementById('temp-val').innerText = data.meteo.temp + "°C";
        document.getElementById('hum-val').innerText = data.meteo.umidita + "%";
        document.getElementById('city-val').innerText = data.meteo.citta;
        document.getElementById('status-val').innerText = data.meteo.condizione;
        document.getElementById('ai-text').innerText = '"' + data.ia_advice + '"';

        myChart.data.labels = data.grafico_ospedali.orari;
        myChart.data.datasets[0].data = data.grafico_ospedali.valori;
        myChart.update();

        map.eachLayer((layer) => {
            if (layer instanceof L.Circle) { map.removeLayer(layer); }
        });

        data.mappa.forEach(zona => {
            const color = zona.rischio === 'alto' ? '#ef4444' : '#f59e0b';
            L.circle([zona.lat, zona.lng], {
                color: color,
                fillColor: color,
                fillOpacity: 0.5,
                radius: 1200
            }).addTo(map)
            .bindPopup(`<b>${zona.nome}</b><br>Temp: ${zona.valore}°C`);
        });

    } catch (error) {
        console.error(error);
        document.getElementById('ai-text').innerText = "⚠️ Errore connessione server";
    }
}

scaricaDatiDaPython();
// setInterval(scaricaDatiDaPython, 180000);