import logging
import time

import pyvisa


logger = logging.getLogger(__name__)

# class PT100Controller:
#     def __init__(self):
#         self.rm = None
#         self.instrument = None
#         self.connected = False
#
#     def connect(self, visa_address="GPIB0::22::INSTR"):
#         """Подключение к Agilent 34970"""
#         try:
#             self.rm = pyvisa.ResourceManager()
#             self.instrument = self.rm.open_resource(visa_address)
#             self.instrument.timeout = 10000
#             self.connected = True
#             logger.info(f"Успешно подключено к {visa_address}")
#             return True
#         except Exception as e:
#             logger.error(f"Ошибка подключения: {e}")
#             return False
#
#     def disconnect(self):
#         """Отключение от прибора"""
#         if self.instrument:
#             self.instrument.close()
#         if self.rm:
#             self.rm.close()
#         self.connected = False
#         logger.info("Отключено от прибора")
#
#     def configure_measurement(self, channels=["101", "102", "103"]):
#         """Настройка измерения температуры PT100"""
#         try:
#             # Сброс прибора
#             self.instrument.write("*RST")
#             time.sleep(1)
#
#             # Настройка для PT100 (4-проводное подключение)
#             for channel in channels:
#                 # FRES - 4-проводное измерение сопротивления
#                 self.instrument.write(f"CONF:FRES {channel}")
#                 # Диапазон 100 Ом для PT100
#                 self.instrument.write(f"FRES:RANGE 100, {channel}")
#                 # Разрешение 0.001 Ом
#                 self.instrument.write(f"FRES:RES 0.001, {channel}")
#                 # NPLC = 1
#                 self.instrument.write(f"FRES:NPLC 1, {channel}")
#
#             logger.info(f"Настроены каналы: {channels}")
#             return True
#         except Exception as e:
#             logger.error(f"Ошибка настройки: {e}")
#             return False
#
#     def read_temperature(self, channels=["101", "102", "103"]):
#         """Чтение температуры с каналов"""
#         try:
#             measurements = {}
#             for channel in channels:
#                 # Чтение сопротивления
#                 resistance = float(self.instrument.query(f"READ? {channel}"))
#                 # Конвертация сопротивления в температуру
#                 temperature = self.resistance_to_temperature(resistance)
#                 measurements[channel] = {
#                     'resistance': round(resistance, 4),
#                     'temperature': temperature,
#                     'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#                 }
#             return measurements
#         except Exception as e:
#             logger.error(f"Ошибка чтения: {e}")
#             return None


class DAQ_34970A():
    def __init__(self, channels: list = None):
        self.channels = channels if not channels else ['205','206','207','208','209','210',]
        self.__device_name = '34970A'
        self.rm = None
        self.instrument = None
        self.connected = False
        self.visa_address: str = ''

    def make_channels_str(self, channels: list)-> str:
        return '(@'+','.join(channels)+')'

    def connect(self) -> bool | None:
        self.rm = pyvisa.ResourceManager()  # '/usr/lib/x86_64-linux-gnu/libiovisa.so'
        list_devices = self.rm.list_resources()
        # print(list_devices)
        for visa_address in list_devices:
            try:
                temp_device = self.rm.open_resource(visa_address)
                temp_name = temp_device.query('*IDN?')
                if self.__device_name in temp_name:
                    # print(temp_name.strip(), '--->>>', visa_address)
                    # temp_device.close()
                    logger.info(f"Successfully connected to {visa_address}")
                    self.instrument = temp_device
                    self.connected = True
                    self.visa_address = visa_address
                    return True
                else:
                    temp_device.close()
                    logger.info(f"Not appropriate device {visa_address}")


            except pyvisa.errors.VisaIOError as e:
                # print('There is not appropriate device or device is not found')
                logger.error(f"This is not appropriate device or device is not found: {e}")
                return False
        return None

    def disconnect(self):
        """Отключение от прибора"""
        if self.instrument:
            self.instrument.close()
        if self.rm:
            self.rm.close()
        self.connected = False
        logger.info(f"Disconnected from {self.visa_address} ")

    def configure(self):
        try:
            # Reset instrument with delay!!!
            self.instrument.write('*RST')
            time.sleep(1)

            self.instrument.write('*CLS')
            self.instrument.write_termination = '\r\n'
            self.instrument.read_termination = '\r\n'

            self.instrument.write(f'CONF:TEMP FRTD, 85, (@{','.join(self.channels)})')
            self.instrument.write(f'TEMP:TRAN:FRTD:RES:REF 100, (@{','.join(self.channels)})')
            self.instrument.write(f'TEMP:TRAN:FRTD:TYPE 85, (@{','.join(self.channels)})')

            self.instrument.write(f'ROUT:SCAN (@{','.join(self.channels)})')

            logger.info(f"Channels: {self.channels} are configured")
            return True
        except Exception as e:
            logger.error(f"Configuration error : {e}")
            return False

    def read_data(self) -> dict:
        self.instrument.write(f'INIT')
        raw_data = self.instrument.query(f'FETC?')
        return dict(zip(self.channels,[float(i) for i in raw_data.split(',')]))

if __name__ == '__main__':

    device = DAQ_34970A()
    device.connect()
    device.configure()
    print(device.read_data())
    device.disconnect()
