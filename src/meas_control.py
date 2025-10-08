import time

import pyvisa

CHANNELS = '(@205:210)'
DEVISE_NAME = '34970A'

class PT100Controller:
    def __init__(self):
        self.rm = None
        self.instrument = None
        self.connected = False

    def connect(self, visa_address="GPIB0::22::INSTR"):
        """Подключение к Agilent 34970"""
        try:
            self.rm = pyvisa.ResourceManager()
            self.instrument = self.rm.open_resource(visa_address)
            self.instrument.timeout = 10000
            self.connected = True
            logger.info(f"Успешно подключено к {visa_address}")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False

    def disconnect(self):
        """Отключение от прибора"""
        if self.instrument:
            self.instrument.close()
        if self.rm:
            self.rm.close()
        self.connected = False
        logger.info("Отключено от прибора")

    def configure_measurement(self, channels=["101", "102", "103"]):
        """Настройка измерения температуры PT100"""
        try:
            # Сброс прибора
            self.instrument.write("*RST")
            time.sleep(1)

            # Настройка для PT100 (4-проводное подключение)
            for channel in channels:
                # FRES - 4-проводное измерение сопротивления
                self.instrument.write(f"CONF:FRES {channel}")
                # Диапазон 100 Ом для PT100
                self.instrument.write(f"FRES:RANGE 100, {channel}")
                # Разрешение 0.001 Ом
                self.instrument.write(f"FRES:RES 0.001, {channel}")
                # NPLC = 1
                self.instrument.write(f"FRES:NPLC 1, {channel}")

            logger.info(f"Настроены каналы: {channels}")
            return True
        except Exception as e:
            logger.error(f"Ошибка настройки: {e}")
            return False

    def read_temperature(self, channels=["101", "102", "103"]):
        """Чтение температуры с каналов"""
        try:
            measurements = {}
            for channel in channels:
                # Чтение сопротивления
                resistance = float(self.instrument.query(f"READ? {channel}"))
                # Конвертация сопротивления в температуру
                temperature = self.resistance_to_temperature(resistance)
                measurements[channel] = {
                    'resistance': round(resistance, 4),
                    'temperature': temperature,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            return measurements
        except Exception as e:
            logger.error(f"Ошибка чтения: {e}")
            return None


def find_device() -> pyvisa.resources.Resource | None:
    rmag = pyvisa.ResourceManager()  # '/usr/lib/x86_64-linux-gnu/libiovisa.so'
    list_devices = rmag.list_resources()
    print(list_devices)
    for device in list_devices:
        try:
            temp_device = rmag.open_resource(device)
            temp_name = temp_device.query('*IDN?')
            if DEVISE_NAME in temp_name:
                print(temp_name.strip(), '--->>>', device)
                # temp_device.close()
                return temp_device

        except pyvisa.errors.VisaIOError:
            print('This is not appropriate device or device is not found')


def configure(device: pyvisa.resources.Resource) -> dict:

    device.write('*RST')
    time.sleep(1)
    device.write('*CLS')
    device.write_termination = '\r\n'
    device.read_termination = '\r\n'
    device.write(f'CONF:TEMP FRTD, 85, {CHANNELS}')
    device.write(f'TEMP:TRAN:FRTD:RES:REF 100, {CHANNELS}')

    # print(device.query(f'TEMP:TRAN:FRTD:RES:REF? {CHANNELS}'))

    device.write(f'TEMP:TRAN:FRTD:TYPE 85, {CHANNELS}')
    # print(device.query(f'TEMP:TRAN:FRTD:TYPE? {CHANNELS}'))

    # print(device.query(f'CONF? {CHANNELS}'))
    device.write(f'ROUT:SCAN {CHANNELS}')
    message = f"{device.query('*IDN?')} --->>> CONFIGURED"
    print(message)
    return {'message': message}


def read_data(device:  pyvisa.resources.Resource) -> dict:
    device.write(f'INIT')
    row_data = device.query(f'FETC?')
    # data = [float(value) for value in row_data.strip().split(',')]
    # print(data)
    return {'data': [float(i) for i in row_data.split(',')]}

if __name__ == '__main__':
    from datetime import datetime
    import os
    # def save_data(d: dict) -> None:
    #     path = './saved_arkolab'
    #     if not os.path.exists(path):
    #         os.makedirs(path)
    #     filename = f'{path}/RT{str(datetime.now())}.csv'
    #     # wb.save(filename)
    #     # wb.close()
    #     with open(filename, 'w') as f:
    #         for key, value in d.items():
    #             f.write(str(key) + ',' + ','.join(str(a) for a in value) + '\n')


    a34970 = find_device()
    # configure(a34970)
    data_dict = {}
    # time_tick = 3
    # for i in range(31):
    #     data_dict[i*time_tick] = read_data(a34970)['data']
    #     print(data_dict[i*time_tick])
    #     time.sleep(time_tick)
    # save_data(data_dict)
    print(read_data(a34970))
    a34970.close()