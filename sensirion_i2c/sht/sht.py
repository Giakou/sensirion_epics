#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import functools
from contextlib import contextmanager
from smbus2 import SMBus

import sensirion_i2c.sht.utils.conversion_utils as conversion_utils
import sensirion_i2c.utils.log_utils as log_utils

logger = log_utils.get_logger()


class SHT:

    def __init__(self):
        # Define properties
        self._addr = None
        self._bus_intf = None
        self._bus = SMBus()
        self.check_crc_bool = True

    @contextmanager
    def i2c_daq(self):
        try:
            self.open_rpi_bus()
            yield
        except FileNotFoundError:
            logger.error(f'Bus interface {self._bus_intf} is not configured for I2C!')
        except (KeyboardInterrupt, SystemExit):
            logger.warning('Killing Thread...')
        finally:
            self.close_rpi_bus()

    def open_rpi_bus(self):
        # Assertion check
        assert self._bus_intf not in [0, 2], f'Bus interface "{self._bus_intf}" is not allowed, because they ' \
                                             f'are reserved! Choose another one!'
        self.bus.open(self._bus_intf)

    def close_rpi_bus(self):
        try:
            self.stop()
        except TypeError:
            logger.warning(f'Bus interface {self._bus_intf} never opened properly!')
        self.bus.close()

    def calculate_crc(kw):
        """Decorator function to calculate crc"""
        def decorator(method):
            @functools.wraps(method)
            def wrapper(self, **kwargs):
                result = method(self, **kwargs)
                if self.check_crc_bool:
                    self.check_crc(kw)
                return result
            return wrapper
        return decorator

    def crc8(self):
        raise NotImplementedError('This function needs to be overwritten by the child class!')

    def check_crc(self, kw='data'):
        """CRC-8 checksum verification"""
        if self.data[2] != self.crc8(self.data[0:2]):
            if kw == 'data':
                logger.warning('CRC Error in temperature measurement!')
            else:
                logger.warning('CRC Error in the first word!')
        if self.data[5] != self.crc8(self.data[3:5]):
            if kw == 'data':
                logger.warning('CRC Error in relative humidity measurement!')
            else:
                logger.warning('CRC Error in the second word!')
        if self.data[2] == self.crc8(self.data[0:2]) and self.data[5] == self.crc8(self.data[3:5]):
            logger.debug('CRC is good')

    @property
    def bus(self):
        """Get the SMBus instance from attribute"""
        return self._bus

    @bus.setter
    def bus(self, value):
        """Set the SMBus instance as attribute"""
        raise AttributeError("The SMBus instance representing the slave device cannot be modified!")

    @property
    def bus_intf(self):
        """Get the I2C bus interface from attribute"""
        return self._bus_intf

    @bus_intf.setter
    def bus_intf(self, value):
        """Set the I2C bus interface as attribute"""
        raise AttributeError("The I2C bus interface which the slave device belongs to is fixed and cannot be modified!")

    @property
    def addr(self):
        """Get the slave address attribute"""
        return self._addr

    @addr.setter
    def addr(self, value):
        """Set the slave address attribute"""
        raise AttributeError("The hex address of the slave device is fixed and cannot be modified!")

    @calculate_crc(kw='sn')
    def _sn(self, cmd):
        """Output of the serial number"""
        self.write_i2c_data_sht(cmd)
        self.data = self.read_i2c_data_sht(6)
        return (self.data[0] << 24) + (self.data[1] << 16) + (self.data[3] << 8) + self.data[4]

    def read_i2c_data_sht(self, length=32):
        return self.bus.read_i2c_block_data(self.addr, 0x00, length)

    def write_i2c_data_sht(self, cmd):
        """Wrapper function for writing block data to SHT85 sensor"""
        if len(cmd) == 1:
            cmd = cmd[0] if isinstance(cmd, list) else cmd
            self.bus.write_byte(self.addr, cmd)
        else:
            self.bus.write_i2c_block_data(self.addr, register=cmd[0], data=cmd[1:])
        time.sleep(conversion_utils.WT[self.rep])

    def general_call_reset(self):
        """General Call mode to rese all devices on the same I2C bus line (not device specific!). This command only
        works if the device is able to process I2C commands."""
        logger.warning('Applying General Call Reset... This is not device specific!')
        self.bus.write_byte(0x00, 0x06)

    def interface_reset(self, addr):
        logger.info('Interface reset...')
        # Toggling SDA
        for i in range(9):
            self.bus.write_byte(addr, 0xFF)
            time.sleep(0.01)

        # Send the Start sequence before the next command
        self.bus.write_byte(addr, 0x35)
        self.bus.write_byte(addr, 0x17)

