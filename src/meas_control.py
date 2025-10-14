import asyncio
import logging
import time
import traceback
from traceback import TracebackException

import pyvisa


logger = logging.getLogger(__name__)

class DAQ_34970A():
    def __init__(self, channels: list = None):
        self.channels = channels if channels else ['205','206','207','208','209','210',]
        self.__device_name = '34970A'
        self.rm = None
        self.instrument = None
        self.connected = False
        self.visa_address: str = ''
        self.is_configured =False
    # def make_channels_str(self, channels: list)-> str:
    #     return '(@'+','.join(channels)+')'

    def connect_sync(self) -> bool | None:
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


    async def connect(self):
        """Async interface connect_sync."""
        await asyncio.to_thread(self.connect_sync)

    def disconnect_sync(self):
        """Disconnection from instrument"""
        if self.instrument:
            self.instrument.close()
        if self.rm:
            self.rm.close()
        self.connected = False
        logger.info(f"Disconnected from {self.visa_address} ")

    async def disconnect(self):
        await asyncio.to_thread(self.disconnect_sync)


    def configure_sync(self):
        try:
            # Reset instrument with delay!!!

            self.instrument.write('*RST')
            time.sleep(1)
            self.instrument.write('*CLS')
            self.instrument.write_termination = '\r\n'
            self.instrument.read_termination = '\r\n'
            str_channels=','.join(self.channels)
            self.instrument.write(f'CONF:TEMP FRTD, 85, (@{str_channels})')
            self.instrument.write(f'TEMP:TRAN:FRTD:RES:REF 100, (@{str_channels})')
            self.instrument.write(f'TEMP:TRAN:FRTD:TYPE 85, (@{str_channels})')

            self.instrument.write(f'ROUT:SCAN (@{str_channels})')

            self.is_configured = True

            logger.info(f"Channels: {self.channels} are configured")
            return True
        except Exception as e:
            logger.error(f"Configuration error : {traceback.format_exc()}")
            return False

    async def configure(self):
        """Async interface configure_sync."""
        await asyncio.to_thread(self.configure_sync)

    def read_data_sync(self) -> dict:
        self.instrument.write(f'INIT')
        raw_data = self.instrument.query(f'FETC?')
        return dict(zip(self.channels,[float(i) for i in raw_data.split(',')]))

    async def read_data(self):
        return await asyncio.to_thread(self.read_data_sync)

if __name__ == '__main__':

    device = DAQ_34970A()
    device.connect()
    device.configure()
    print(device.read_data())
    device.disconnect()
