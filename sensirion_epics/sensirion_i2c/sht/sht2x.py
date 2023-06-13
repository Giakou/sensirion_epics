#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SHT2x Python wrapper library of smbus2
"""

import time

import sensirion_epics.sensirion_i2c.sensirion_i2c as sensirion
import sensirion_epics.utils.log_utils as log_utils
import sensirion_epics.sensirion_i2c.sht.sht as sht

logger = log_utils.get_logger()


class SHT2x(sht.SHT):
    """SHT2x class"""
    def __init__(self, bus_intf=1, mode='hold'):
        """Constructor"""
        super().__init__()
        self._addr = 0x40
        self._bus_intf = bus_intf
        assert mode in ['hold', 'no_hold']
        self.mode = mode

    @property
    def sn(self):
        """Get S/N"""
        return self._sn(cmd=[0xFA, 0x0F])

    @sensirion.printer
    def reset(self):
        """Apply Soft Reset"""
        logger.debug('Applying Soft Reset...')
        self.write_data_i2c([0xFE])

    def single_shot(self, param):
        """Single temperature or relative humidity measurement in hold or no-hold master mode"""
        cmd_dict = {
            't': {
                'hold': [0xE3],
                'no_hold': [0xF3]
            },
            'rh': {
                'hold': [0xE5],
                'no_hold': [0xF5]
            }
        }
        assert param in cmd_dict.keys()
        self.write_data_i2c(cmd_dict[param][self.mode])
        self.read_measurement()

    @sensirion.printer
    def single_shot_with_heat(self, mwatt, duration):
        """Single temperature or relative humidity measurement in hold or no-hold master mode"""
        heater_desc = {
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
        assert mwatt in heater_desc.keys()
        assert duration in heater_desc[200].keys()
        self.write_data_i2c(heater_desc[mwatt][duration])
        time.sleep(duration)
        self.read_measurement()

    def temp_conversion(self, temp_digital):
        """Calculate temperature from data"""
        # Significant digits based on the SHT21 resolution of 0.01 °C
        return round(-46.85 + 175.72 * temp_digital / (2 ** 16 - 1), 2)

    def rhw_conversion(self, rh_digital):
        """Calculate relative humidity from data"""
        # Significant digits based on the SHT21 resolution of 0.04 %RH
        rh_analog = round(-6 + 125 * rh_digital / (2 ** 16 - 1), 2)
        # Make sure that relative humidity never returns a 0% value, otherwise the dew point calculation will fail
        rh_analog = 1e-3 if rh_analog < 0.01 else rh_analog
        return rh_analog
