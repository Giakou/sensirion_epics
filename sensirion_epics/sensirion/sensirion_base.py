#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import abc
import functools
import time

from smbus2 import SMBus
from contextlib import contextmanager

import sensirion_epics.sensirion.sht.utils.conversion_utils as cu
import sensirion_epics.utils.log_utils as log_utils

logger = log_utils.get_logger()


def printer(func):
    """Decorator function to inform the user that write/read command was successful"""
    @functools.wraps(func)
    def wrapper(self, **kwargs):
        func(self, **kwargs)
        logger.debug('Done!')
    return wrapper


def calculate_crc(func):
    """Decorator function to calculate CRC-8"""
    @functools.wraps(func)
    def wrapper(self, **kwargs):
        func(self, **kwargs)
        if self.check_crc_bool:
            self.check_crc()
    return wrapper


def crc8(buffer):
    """CRC-8 checksum calculation from data"""
    # Initialize the checksum with a byte full of 1s
    crc = 0xFF
    # Polynomial to divide with
    polynomial = 0x131
    for byte in buffer:
        # Perform XOR operation between the crc and the byte
        crc ^= byte
        for _ in range(8):
            # Extract the leftmost bit of the CRC register
            bit = crc & 0x80
            # Shift the crc register by one bit to the left
            crc <<= 1
            # If leftmost bit is 1 perform XOR between CRC and polynomial
            if bit:
                crc ^= polynomial
        # Mask the original value to ensure that it remains within the range of 8 bits (final XOR)
        crc ^= 0x00
    return crc


class SensirionBase(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def __init__(self):
        pass


class SensirionI2C(SensirionBase):

    def __init__(self):
        # Define properties
        self._addr = None
        self._bus_intf = None
        self.check_crc_bool = True
        self._bus = SMBus()
        self._buffer = None

    @property
    @abc.abstractmethod
    def sn(self):
        pass

    @sn.setter
    def sn(self, value):
        raise AttributeError("The S/N of the slave device is unique and cannot be modified!")

    @property
    def addr(self):
        """Get the slave address attribute"""
        return self._addr

    @addr.setter
    def addr(self, value):
        """Set the slave address attribute"""
        raise AttributeError("The hex address of the slave device is fixed and cannot be modified!")

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
    def buffer(self):
        """Get data from buffer"""
        return self._buffer

    @buffer.setter
    def buffer(self, value):
        """Write user data in buffer"""
        raise AttributeError("The user is not allowed to write anything in the buffer!")

    def stop(self):
        """Dummy method for implementing break command to stop continuous measurement. The method is not overwritten if
        the break command is not implemented in the sensor."""
        pass

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

    def check_crc(self):
        """CRC-8 checksum verification"""
        crc_status = True
        for n in range(0, len(self.buffer), 3):
            if self.buffer[n+2] != crc8(self.buffer[n:n+2]):
                logger.warning(f'CRC Error in the word{n//3}!')
                crc_status = False
        if crc_status:
            logger.debug('CRC is good')

    def write_data_i2c(self, cmd):
        """Wrapper function for writing block data to SHT85 sensor"""
        if len(cmd) == 1:
            cmd = cmd[0] if isinstance(cmd, list) else cmd
            self.bus.write_byte(self.addr, cmd)
        else:
            self.bus.write_i2c_block_data(self.addr, register=cmd[0], data=cmd[1:])
        try:
            time.sleep(cu.WT[self.rep])
        except AttributeError:
            time.sleep(0.005)

    def read_data_i2c(self, length=32):
        self._buffer = self.bus.read_i2c_block_data(self.addr, 0x00, length)

    # FIXME: Not tested!
    def general_call_reset(self):
        """General Call mode to reset all devices on the same I2C bus line (not device specific!). This command only
        works if the device is able to process I2C commands."""
        logger.warning('Applying General Call Reset... This is not device specific!')
        self.bus.write_byte(0x00, 0x06)

    # FIXME: Not tested!
    def interface_reset(self, addr):
        logger.info('Interface reset...')
        # Toggling SDA
        for i in range(9):
            self.bus.write_byte(addr, 0xFF)
            time.sleep(0.01)

        # Send the Start sequence before the next command
        self.bus.write_byte(addr, 0x35)
        self.bus.write_byte(addr, 0x17)


class SensirionRS485(metaclass=abc.ABCMeta):

    def __init__(self):
        pass


class SensirionRS232(metaclass=abc.ABCMeta):

    def __init__(self):
        pass


class SensirionPWM(metaclass=abc.ABCMeta):

    def __init__(self):
        pass


class SensirionSensibus(metaclass=abc.ABCMeta):

    def __init__(self):
        pass


class SensirionSDM(metaclass=abc.ABCMeta):

    def __init__(self):
        pass


class SensirionSPI(metaclass=abc.ABCMeta):

    def __init__(self):
        pass


class SensirionUART(metaclass=abc.ABCMeta):

    def __init__(self):
        pass


class SensirionModBus(metaclass=abc.ABCMeta):

    def __init__(self):
        pass


class SensirionLIN(metaclass=abc.ABCMeta):

    def __init__(self):
        pass


class SensirionAnalogVoltage(metaclass=abc.ABCMeta):
    def __init__(self):
        pass


class SensirionAnalogCurrent(metaclass=abc.ABCMeta):
    def __init__(self):
        pass


class SensirionProfiBus(metaclass=abc.ABCMeta):
    def __init__(self):
        pass


class SensirionIOLink(metaclass=abc.ABCMeta):
    def __init__(self):
        pass


class SensirionSwitch(metaclass=abc.ABCMeta):
    def __init__(self):
        pass


class SensirionDeviceNet(metaclass=abc.ABCMeta):
    def __init__(self):
        pass
