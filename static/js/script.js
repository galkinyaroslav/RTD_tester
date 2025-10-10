let temperatureChart;
let websocket;
let reconnectTimeout;
const maxReconnectAttempts = 5;
let reconnectAttempts = 0;

const chartData = {
    labels: [],
    datasets: []
};

// Инициализация WebSocket соединения
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    websocket = new WebSocket(wsUrl);

    websocket.onopen = function (event) {
        console.log('WebSocket подключен');
        updateConnectionStatus(true);
        reconnectAttempts = 0;
    };

    websocket.onmessage = function (event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    websocket.onclose = function (event) {
        console.log('WebSocket отключен');
        updateConnectionStatus(false);
        scheduleReconnect();
    };

    websocket.onerror = function (error) {
        console.error('WebSocket ошибка:', error);
        updateConnectionStatus(false);
    };
}

function scheduleReconnect() {
    if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        const timeout = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
        console.log(`Попытка переподключения ${reconnectAttempts} через ${timeout}ms`);
        reconnectTimeout = setTimeout(connectWebSocket, timeout);
    }
}

function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connectionStatus');
    if (connected) {
        statusElement.textContent = 'WebSocket: Подключен';
        statusElement.className = 'connection-status connected';
    } else {
        statusElement.textContent = 'WebSocket: Отключен';
        statusElement.className = 'connection-status disconnected';
    }
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'data':
            updateData(data.data);
            break;
        case 'status':
            updateStatus(data);
            break;
    }
}

// Инициализация графика
function initializeChart() {
    const ctx = document.getElementById('temperatureChart').getContext('2d');
    temperatureChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                y: {
                    title: {
                        display: true,
                        text: 'Температура (°C)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Время',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: 'rgba(0,0,0,0.1)'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleFont: {
                        size: 13
                    },
                    bodyFont: {
                        size: 13
                    }
                }
            }
        }
    });
}

// Обновление данных на странице
function updateData(data) {
    const dataGrid = document.getElementById('dataGrid');

    Object.entries(data).forEach(([channel, values]) => {
        let card = dataGrid.querySelector(`[data-channel="${channel}"]`);

        if (!card) {
            card = document.createElement('div');
            card.className = 'data-card';
            card.setAttribute('data-channel', channel);
            card.innerHTML = `
                        <h3>Канал ${channel}</h3>
                        <div class="temperature">-- °C</div>
                        <div class="resistance">-- Ω</div>
                        <div class="timestamp">--</div>
                    `;
            dataGrid.appendChild(card);
        }

        card.querySelector('.temperature').textContent = `${values.temperature} °C`;
        card.querySelector('.resistance').textContent = `${values.resistance} Ω`;
        card.querySelector('.timestamp').textContent = values.timestamp;
    });

    updateChart(data);
}

// Обновление графика
function updateChart(data) {
    const now = new Date().toLocaleTimeString();

    chartData.labels.push(now);
    if (chartData.labels.length > 50) {
        chartData.labels.shift();
    }

    Object.entries(data).forEach(([channel, values]) => {
        let dataset = chartData.datasets.find(ds => ds.label === `Канал ${channel}`);

        if (!dataset) {
            const colors = [
                '#007bff', '#28a745', '#dc3545',
                '#ffc107', '#6f42c1', '#e83e8c'
            ];
            dataset = {
                label: `Канал ${channel}`,
                data: [],
                borderColor: colors[chartData.datasets.length % colors.length],
                backgroundColor: colors[chartData.datasets.length % colors.length] + '20',
                borderWidth: 3,
                pointBackgroundColor: colors[chartData.datasets.length % colors.length],
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.1,
                fill: false
            };
            chartData.datasets.push(dataset);
        }

        dataset.data.push(values.temperature);
        if (dataset.data.length > 50) {
            dataset.data.shift();
        }
    });

    chartData.datasets.forEach(dataset => {
        if (dataset.data.length > 50) {
            dataset.data = dataset.data.slice(-50);
        }
    });

    temperatureChart.update('none');
}

// Обновление статуса
function updateStatus(status) {
    const measuringElement = document.getElementById('statusMeasuring');
    const recordingElement = document.getElementById('statusRecording');
    const connectedElement = document.getElementById('statusConnected');

    // Обновление статуса измерений
    if (status.measuring) {
        measuringElement.textContent = '📊 Измерения: Активны';
        measuringElement.className = 'status-card status-measuring';
    } else {
        measuringElement.textContent = '📊 Измерения: Остановлены';
        measuringElement.className = 'status-card status-inactive';
    }

    // Обновление статуса записи
    if (status.recording) {
        recordingElement.textContent = '💾 Запись: Активна';
        recordingElement.className = 'status-card status-recording';
    } else {
        recordingElement.textContent = '💾 Запись: Неактивна';
        recordingElement.className = 'status-card status-inactive';
    }

    // Обновление статуса подключения
    if (status.connected) {
        connectedElement.textContent = '🔌 Прибор: Подключен';
        connectedElement.className = 'status-card status-connected';
    } else {
        connectedElement.textContent = '🔌 Прибор: Отключен';
        connectedElement.className = 'status-card status-inactive';
    }

    // Обновление состояния кнопок
    updateButtonStates(status);
}

function updateButtonStates(status) {
    document.getElementById('btnStart').disabled = status.measuring;
    document.getElementById('btnStop').disabled = !status.measuring;
    document.getElementById('btnRecordStart').disabled = !status.measuring || status.recording;
    document.getElementById('btnRecordStop').disabled = !status.measuring || !status.recording;
}

// API вызовы
async function apiCall(endpoint, method = 'POST') {
    try {
        const response = await fetch(`/api${endpoint}`, {method});
        return await response.json();
    } catch (error) {
        console.error(`Ошибка API ${endpoint}:`, error);
        alert('Ошибка связи с сервером');
        return {status: 'error', message: 'Ошибка связи'};
    }
}

// Обработчики кнопок
document.getElementById('btnStart').addEventListener('click', async () => {
    const result = await apiCall('/start');
    console.log('Start:', result);
});

document.getElementById('btnStop').addEventListener('click', async () => {
    const result = await apiCall('/stop');
    console.log('Stop:', result);
});

document.getElementById('btnRecordStart').addEventListener('click', async () => {
    const result = await apiCall('/record/start');
    console.log('Record start:', result);
});

document.getElementById('btnRecordStop').addEventListener('click', async () => {
    const result = await apiCall('/record/stop');
    console.log('Record stop:', result);
});

document.getElementById('btnDownload').addEventListener('click', async () => {
    window.open('/api/download', '_blank');
});

// Инициализация
initializeChart();
connectWebSocket();

// Получение начального статуса
fetch('/api/status')
    .then(response => response.json())
    .then(updateStatus)
    .catch(console.error);

// Периодическая проверка статуса (резервный канал)
setInterval(async () => {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();
        updateStatus(status);
    } catch (error) {
        console.error('Ошибка проверки статуса:', error);
    }
}, 5000);
