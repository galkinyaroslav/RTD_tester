// script.js — универсальный, устойчивый обработчик WS + Chart + карточки

document.addEventListener("DOMContentLoaded", () => {
        console.log("DOM loaded");
        const wsUrl = `ws://${window.location.host}/pt100/ws`; // поправь, если у тебя другой путь
        const connectionStatus = document.getElementById("connectionStatus");
        const dataGrid = document.getElementById("dataGrid");
        const canvas = document.getElementById("temperatureChart");
        if (!canvas) {
            console.error("Canvas #temperatureChart not found");
            return;
        }

        let ws = null;
        let chart = null;
        let channels = [];         // ordered array of channel keys as strings
        const datasetsMap = {
            labels: [],
            datasets: [{},]
        };        // key -> dataset object (Chart dataset)
        // let history = {};            // key -> [{x:Date, y:Number},...]

        function log(...args) {
            console.log("[pt100-ui]", ...args);
        }

        function warn(...args) {
            console.warn("[pt100-ui]", ...args);
        }

        function error(...args) {
            console.error("[pt100-ui]", ...args);
        }

        function updateConnectionStatus(connected) {
            if (!connectionStatus) return;
            connectionStatus.textContent = connected ? "WebSocket: Подключен" : "WebSocket: Отключен";
            connectionStatus.classList.toggle("connected", connected);
            connectionStatus.classList.toggle("disconnected", !connected);
        }

        function stableKeys(obj) {
            return Object.keys(obj).sort((a, b) => Number(a) - Number(b));
        }

        function ensureChartExists() {
            if (chart) return;
            const ctx = canvas.getContext("2d");

            chart = new Chart(ctx, {
                type: "line",
                data: datasetsMap,
                options: {
                    responsive: true,
                    animation: false,
                    scales: {
                        x: {
                            // type: "time",
                            // time: {unit: "second", tooltipFormat: 'HH:mm:ss'},
                            // ticks: {maxTicksLimit: 10}
                        },
                        y: {
                            beginAtZero: false,
                            title: {display: true, text: "°C"}
                        }
                    },
                    plugins: {legend: {position: "top"}}
                }
            });
        }

        function rebuildUIAndChart(newKeys) {
            log("Rebuilding UI and chart for keys:", newKeys);
            // rebuild data-grid
            dataGrid.innerHTML = "";
            channels = newKeys.slice();
            history = {};
            datasetsMap.labels = [];
            datasetsMap.datasets = [];

            for (const k of channels) {
                // create card
                const card = document.createElement("div");
                card.className = "data-card";
                card.innerHTML = `<h3>Канал ${k}</h3><div class="temperature" id="t${k}">-- °C</div>`;
                dataGrid.appendChild(card);
                history[k] = [];
            }

            // rebuild chart datasets
            if (chart) {

                chart.data = datasetsMap; // clear
            } else {
                ensureChartExists();
            }

            for (const k of channels) {

                const ds = {
                    label: `Канал ${k}`,
                    data: [], // will be array of {x: Date, y: Number}
                    borderWidth: 2,
                    // tension: 0.15,
                    // fill: false,
                    // parsing: false
                };
                datasetsMap.datasets.push(ds);
                // chart.data.datasets.push(ds);
                console.log('datasetsMap[k]=', datasetsMap[k]);


            }
            // console.log('datasetsMap=',datasetsMap);
            //
            // console.log('CHARTDATASET',chart.data.datasets);

            chart.update();
        }

        function onMessageData(t_values) {
            // t_values expected to be object like {'204': 21.883, ...}
            if (!t_values || typeof t_values !== "object") return;
            const keys = stableKeys(t_values);

            // rebuild UI if channel set changed
            const needRebuild = (keys.length !== channels.length) || keys.join() !== channels.join();
            if (needRebuild) {
                rebuildUIAndChart(keys);
            }

            const now = new Date().toLocaleTimeString();
            datasetsMap.labels.push(now);
            for (const k of keys) {
                const v = t_values[k];
                const el = document.getElementById(`t${k}`);
                if (el) {
                    if (typeof v === "number") el.textContent = `${v.toFixed(3)} °C`;
                    else el.textContent = "-- °C";
                }
            }

            for (let i = 0; i < keys.length; i++) {
                datasetsMap.datasets[i].data.push(t_values[keys[i]]);
            }

            console.log('chart.data.datasets=', chart.data.datasets)
            console.log('datasetsMap', datasetsMap)
            // update chart
            try {
                chart.update();
            } catch (e) {
                console.warn("Chart update failed:", e);
            }
        }

        function connect() {
            log("Connecting to WS", wsUrl);
            try {
                ws = new WebSocket(wsUrl);
            } catch (e) {
                error("WebSocket constructor error", e);
                setTimeout(connect, 3000);
                return;
            }

            ws.onopen = () => {
                log("WS open");
                updateConnectionStatus(true);
            };
            ws.onclose = (ev) => {
                warn("WS closed", ev);
                updateConnectionStatus(false);
                setTimeout(connect, 3000);
            };
            ws.onerror = (ev) => {
                warn("WS error", ev);
                updateConnectionStatus(false);
            };
            ws.onmessage = (ev) => {
                // ev.data is stringified JSON
                try {
                    const msg = JSON.parse(ev.data);
                    // support both {"data": {...}} and {"message": {...}} or raw object
                    const payload = msg?.data ?? msg?.message ?? msg;
                    log("New data:", payload);
                    onMessageData(payload);
                } catch (err) {
                    console.warn("Failed parse WS message", err, ev.data);
                }
            };
        }

        // ensure Chart.js exists
        if (typeof Chart === "undefined") {
            error("Chart.js not found. Add <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>' to HTML.");
            return;
        }

        // Try to detect whether time adapter is present; if not, give friendly warning
        try {
            // attempt to create (will use adapter if available). If adapter missing Chart may still work with category axis
            ensureChartExists();
        } catch (e) {
            warn("Failed to init chart with time scale; falling back to category x-axis", e);
            chart = new Chart(canvas.getContext("2d"), {
                type: "line",
                data: {datasets: []},
                options: {scales: {x: {type: "category"}, y: {}}}
            });
        }

        connect();

        function updateStatus(status) {
            const measuringElement = document.getElementById('statusMeasuring');
            const runnumberElement = document.getElementById('statusRunNumber');
            const connectedElement = document.getElementById('statusConnected');

            // Обновление статуса измерений
            if (status.measuring) {
                measuringElement.textContent = '📊 Измерения: Активны';
                measuringElement.className = 'status-card status-measuring';
            } else {
                measuringElement.textContent = '📊 Измерения: Остановлены';
                measuringElement.className = 'status-card status-inactive';
            }

            runnumberElement.textContent = '💾 Run number: ' + status.run_number;


            if (status.connected) {
                connectedElement.textContent = '🔌 Прибор: Подключен';
                connectedElement.className = 'status-card status-connected';
            } else {
                connectedElement.textContent = '🔌 Прибор: Отключен';
                connectedElement.className = 'status-card status-inactive';
            }
        }

        btnStart.addEventListener("click", async () => {
            const timer = parseInt(timerInput.value);

            // chart.destroy();
            // datasetsMap.datasets.data = [];
            // datasetsMap.labels = [];
            // chart.data = datasetsMap;
            chart.clear();
            rebuildUIAndChart(channels);
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

        btnExcel.addEventListener("click", async () => {
            await fetch("/pt100/to_excel", {method: "POST"});
        });

        btnStop.addEventListener("click", async () => {
            const response = await fetch("/pt100/api/stop", {method: "POST"});
            const data = await response.json();
            console.log("⏹️ Измерения остановлены:", data);
            if (data.status === "stopped") {
                btnStart.disabled = false;
                btnStop.disabled = true;

            }
        });

        fetch('/pt100/api/status',{method: "GET"})
            .then(response => response.json())
            .then(updateStatus)
            .catch(console.error);

// Периодическая проверка статуса (резервный канал)
        setInterval(async () => {
            try {
                const response = await fetch('/pt100/api/status',{method: "GET"});
                const status = await response.json();
                updateStatus(status);
            } catch (error) {
                console.error('Ошибка проверки статуса:', error);
            }
        }, 5000);

    }
);
