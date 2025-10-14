document.addEventListener("DOMContentLoaded", () => {
        // console.log(`${window.location.host}`); // 127.0.0.1:8000

    const ws = new WebSocket(`ws://${window.location.host}/pt100/ws`);//pt100 add to endpoint
    const btnStart = document.getElementById("btnStart");
    const btnStop = document.getElementById("btnStop");
    const timerInput = document.getElementById("timerInput");

    const ctx = document.getElementById("temperatureChart").getContext("2d");
    const chartData = {
        labels: [],
        datasets: [
            { label: "T205", data: [], borderWidth: 2 },
            { label: "T206", data: [], borderWidth: 2 },
            { label: "T207", data: [], borderWidth: 2 },
            { label: "T208", data: [], borderWidth: 2 },
            { label: "T209", data: [], borderWidth: 2 },
            { label: "T210", data: [], borderWidth: 2 },
        ]
    };
    const chart = new Chart(ctx, {
        type: "line",
        data: chartData,
        options: {
            animation: false,
            scales: {
                y: { beginAtZero: false },
            }
        }
    });

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.data) {
            const t = new Date().toLocaleTimeString();
            chartData.labels.push(t);
            const temps = Object.values(msg.data);
            temps.forEach((v, i) => chartData.datasets[i].data.push(v));
            chart.update();
        }
    };

    btnStart.addEventListener("click", async () => {
        const timer = parseInt(timerInput.value);
        await fetch("/api/state/timer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ timer }),
        });
        await fetch("/api/start", { method: "POST" });
        btnStart.disabled = true;
        btnStop.disabled = false;
    });

    btnStop.addEventListener("click", async () => {
        await fetch("/api/stop", { method: "POST" });
        btnStart.disabled = false;
        btnStop.disabled = true;
    });
});

