// document.addEventListener("DOMContentLoaded", () => {
    console.log("✅ DOM fully loaded");

    // console.log(`${window.location.host}`); // 127.0.0.1:8000
    const connectionStatus = document.getElementById("connectionStatus");
    const btnStart = document.getElementById("btnStart");
    const btnStop = document.getElementById("btnStop");
    const timerInput = document.getElementById("timerInput");
    const t205 = document.getElementById('t205')
    const t206 = document.getElementById('t206')
    const t207 = document.getElementById('t207')
    const t208 = document.getElementById('t208')
    const t209 = document.getElementById('t209')
    const t210 = document.getElementById('t210')
    let card = [t205,t206,t207,t208,t209,t210]
    let ws = null;

    const ctx = document.getElementById("temperatureChart").getContext("2d");
    const chartData = {
        labels: [],
        datasets: [
            {label: "T205", data: [], borderWidth: 2},
            {label: "T206", data: [], borderWidth: 2},
            {label: "T207", data: [], borderWidth: 2},
            {label: "T208", data: [], borderWidth: 2},
            {label: "T209", data: [], borderWidth: 2},
            {label: "T210", data: [], borderWidth: 2},
        ]
    };
    const chart = new Chart(ctx, {
        type: "line",
        data: chartData,
        options: {
            animation: false,
            scales: {
                y: {beginAtZero: false},
            }
        }
    });

    // const ws = new WebSocket(`ws://${window.location.host}/pt100/ws`);//pt100 add to endpoint

    function updateConnectionStatus(connected) {
        if (connected) {
            connectionStatus.textContent = "WebSocket: Подключен";
            connectionStatus.classList.remove("disconnected");
            connectionStatus.classList.add("connected");
        } else {
            connectionStatus.textContent = "WebSocket: Отключен";
            connectionStatus.classList.remove("connected");
            connectionStatus.classList.add("disconnected");
        }
    }

    function connectWebSocket() {
        ws = new WebSocket(`ws://${window.location.host}/pt100/ws`);

        ws.onopen = () => {
            console.log("✅ WebSocket подключен");
            updateConnectionStatus(true);
        };

        ws.onclose = () => {
            console.log("⚠️ WebSocket отключен");
            updateConnectionStatus(false);
            // Автопереподключение через 5 секунд
            setTimeout(connectWebSocket, 5000);
        };

        ws.onerror = (err) => {
            console.error("Ошибка WebSocket:", err);
            updateConnectionStatus(false);
        };

        ws.onmessage = (event) => {
            try {

                const msg = JSON.parse(event.data);
                console.log("📡 Новые данные:", msg);
                // console.log("📡 Data:", msg.data);
                // console.log("📡 Data:", msg.data);


                if (msg.data) {
                    const t = new Date().toLocaleTimeString();
                    console.log("📡 Новые T:", t);

                    chartData.labels.push(t);
                    const temps = Object.values(msg.data);
                    temps.forEach((v, i) => chartData.datasets[i].data.push(v));
                    chart.update();
                    console.log(card)
                    temps.forEach((v, i) => card[i].textContent = v + ' °C');


                }
            } catch (err) {
                console.warn("Ошибка обработки сообщения:", err);
            }
        };
    }

    connectWebSocket(); // подключаемся при загрузке страницы


    // === Кнопки управления ===
    btnStart.addEventListener("click", async () => {
        const timer = parseInt(timerInput.value);
        // chart.destroy();
        await fetch("/pt100/api/configure", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
        });


        await fetch("/pt100/api/state/timer", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({timer})
        });

        const response = await fetch("/pt100/api/start", {method: "POST"});
        const data = await response.json();
        console.log("▶️ Измерения запущены:", data);

        btnStart.disabled = true;
        btnStop.disabled = false;
    });

    btnStop.addEventListener("click", async () => {
        const response = await fetch("/pt100/api/stop", {method: "POST"});
        const data = await response.json();

        if (data.status === "stopped") {
            btnStart.disabled = false;
            btnStop.disabled = true;
        }
    });
// });

