import asyncio
import json
import logging
from _datetime import datetime
import time

import pandas as pd

from src.meas_control import DAQ_34970A
from src.state import MeasurementState
from src.web_socket import ConnectionManager

logger = logging.getLogger(__name__)

def measurement_loop(state: MeasurementState, pt100_controller: DAQ_34970A, manager: ConnectionManager):
    """Цикл измерения в отдельном потоке"""

    while state.is_measuring:
        try:
            measurements = pt100_controller.read_data()
            if measurements:
                state.current_data = measurements

                # Асинхронная рассылка данных через WebSocket
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast(json.dumps({
                        'type': 'data',
                        'data': measurements
                    })),
                    asyncio.get_event_loop()
                )

                # Запись в буфер если включена запись
                if state.is_recording:
                    record = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                        **{f"temp_{ch}": measurements[ch] for ch in pt100_controller.channels},
                    }
                    state.data_buffer.append(record)
                    logger.info(f"Data have been written: {measurements}")

            time.sleep(1)

        except Exception as e:
            logger.error(f"Error in measurement cycle: {e}")
            time.sleep(1)

def save_to_excel(state ):
    """Сохранение данных из буфера в Excel"""

    if state.data_buffer:
        try:
            df = pd.DataFrame(state.data_buffer)

            try:
                existing_df = pd.read_excel(state.excel_filename)
                df = pd.concat([existing_df, df], ignore_index=True)
            except FileNotFoundError:
                pass

            df.to_excel(state.excel_filename, index=False)
            logger.info(f"Данные сохранены в {state.excel_filename}, записей: {len(state.data_buffer)}")
            state.data_buffer = []
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения в Excel: {e}")
            return False
    return True