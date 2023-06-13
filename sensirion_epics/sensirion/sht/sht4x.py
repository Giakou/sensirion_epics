#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SHT85 Python wrapper library of smbus2
"""

import functools
import time

import sensirion_epics.utils.log_utils as log_utils
import sensirion_epics.sensirion_i2c.sht.sht as sht

logger = log_utils.get_logger()


def printer(func):
    """Decorator function to Inform the user that write/read command was successful"""
    @functools.wraps(func)
    def wrapper(self, **kwargs):
        func(self, **kwargs)
        logger.debug('Done!')
    return wrapper


class SHT4x(sht.SHT):
    """SHT4x class"""
    def __init__(self, addr, bus_intf=1, rep='high'):
        """Constructor"""
        super().__init__()
        self._bus_intf = bus_intf
        assert addr in [0x44, 0x45, 0x46], 'The hex address can be either 0x44 or 0x45'
        self._addr = addr
        # Assertion checks
        assert rep in ['high', 'medium', 'low'], f'Repetition number "{rep}" is not allowed, ' \
                                                 'only "high", "medium" or "low"!'
        self.rep = rep

    @property
    def sn(self):
        return self._sn(cmd=[0x89])

    @sn.setter
    def sn(self, value):
        raise AttributeError("The S/N of the slave device is unique and cannot be modified!")

    @printer
    def reset(self):
        """Apply Soft Reset"""
        logger.debug('Applying Soft Reset...')
        self.write_data_i2c([0x94])

    def single_shot(self):
        repeatability = {
            'high': [0xFD],
            'medium': [0xF6],
            'low': [0xE0]
        }
        self.write_data_i2c(repeatability[self.rep])
        self.read_measurement()

    @printer
    def single_shot_with_heat(self, mwatt, duration):
        cmd_dict = {
            200: {
                1: [0x39],
                0.1: [0x32]
            },
            110: {
                1: [0x2F],
                0.1: [0x24]
            },
            20: {
                1: [0x1E],
                0.1: [0x15]
            }
        }
        assert mwatt in cmd_dict.keys()
        assert duration in cmd_dict[200].keys()
        self.write_data_i2c(cmd_dict[mwatt][duration])
        time.sleep(duration)
        self.read_measurement()

    def temp_conversion(self, temp_digital):
        """Calculate temperature from data"""
        # Significant digits based on the SHT21 resolution of 0.01 °C
        return round(-45 + 175 * temp_digital / (2 ** 16 - 1), 2)

    def rhw_conversion(self, rh_digital):
        """Calculate relative humidity from data"""
        # Significant digits based on the SHT21 resolution of 0.04 %RH
        rh_analog = round(-6 + 125 * rh_digital / (2 ** 16 - 1), 2)
        # Make sure that relative humidity never returns a 0% value, otherwise the dew point calculation will fail
        rh_analog = 1e-3 if rh_analog < 0.01 else rh_analog
        return rh_analog
