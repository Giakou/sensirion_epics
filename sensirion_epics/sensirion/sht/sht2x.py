#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SHT2x Python wrapper library of smbus2
"""

import sensirion_epics.sensirion.sensirion_base as sensirion
import sensirion_epics.sensirion.sht.utils.conversion_utils as cu
import sensirion_epics.utils.log_utils as log_utils
import sensirion_epics.sensirion.sht.sht as sht

logger = log_utils.get_logger()


class SHT2x(sht.SHT):
    """SHT2x class"""

    _wait_times = {
        't': 0.085,
        'rh': 0.029
    }

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

    @property
    def user_register(self):
        """Return User Register content"""
        self.write_data_i2c([0xE7], wait=0.015)
        self.read_data_i2c(1)
        return self.buffer

    @user_register.setter
    @sensirion.printer
    def user_register(self, status):
        """Set User Register bits"""
        self.write_data_i2c([0xE6, status], wait=0.015)

    @sensirion.printer
    def reset(self):
        """Apply Soft Reset"""
        logger.debug('Applying Soft Reset...')
        self.write_data_i2c([0xFE], wait=0.015)

    @sensirion.calculate_crc
    def read_measurement(self, param):
        """Readout measurement data"""
        assert param in ['t', 'rh']
        # The measurement data consists of 6 bytes (2 for each measurement value and 1 for each checksum)
        self.read_data_i2c(3)
        # Set the two least significant bits (status bits) to 0
        digital_value = (self.buffer[0] << 8 | self.buffer[1]) & 0xFFFC
        if param == 't':
            self.t = self.temp_conversion(digital_value)
        else:
            rhw = self.rhw_conversion(digital_value)
            # Sensirion is calibrating most of their sensors using the magnus coefficients above water, even for t < 0 °C
            self.rh = rhw if self.t >= -45 else self.rhi_conversion(rhw)

    def single_shot_t(self):
        """Single temperature measurement in hold or no-hold master mode"""
        cmd = {
            'hold': [0xE3],
            'no_hold': [0xF3]
        }
        self.write_data_i2c(cmd[self.mode], wait=self.__class__._wait_times['t'])
        self.read_measurement('t')

    def single_shot_rh(self):
        """Single relative humidity measurement in hold or no-hold master mode"""
        cmd = {
            'hold': [0xE5],
            'no_hold': [0xF5]
        }
        self.write_data_i2c(cmd[self.mode], wait=self.__class__._wait_times['rh'])
        self.read_measurement('rh')

    def single_shot(self):
        """Succession of a temperature and a relative humidity measurement in hold or no-hold master mode"""
        self.single_shot_t()
        self.single_shot_rh()
        self.dp = cu.dew_point(self.t, self.rh)

    @property
    def measurement_resolution(self):
        content_byte = self.user_register
        # string representation of resolution bits for RH and T
        return [content_byte >> 7, content_byte & 0x1]

    @measurement_resolution.setter
    def measurement_resolution(self, state):
        assert len(state) == 2
        for bit in state:
            assert bit in [0, 1]
        status = self.user_register
        # Change bit 7 based on the state
        status |= state[0] << 7
        # Change bit 0 based on the state
        status |= state[1]
        # Write user register
        self.user_register = status

    @property
    def heater(self):
        """Return heater bit from User Register content"""
        return (self.user_register >> 2) & 0x1

    @heater.setter
    def heater(self, state):
        """Set heater bit in User Register"""
        assert state in [0, 1]
        status = self.user_register
        self.user_register = status & 0xFF if state else status & 0xFB

    @property
    def otp_reload(self):
        """Get OTP reload value. Default is '1'"""
        return (self.user_register >> 1) & 0x1

    @otp_reload.setter
    def otp_reload(self, state):
        """set to '0' to load the default settings after each time a measurement command is issued. Default is '1'"""
        assert state in [0, 1]
        status = self.user_register
        self.user_register = status & 0xFF if state else status & 0xFD

    @property
    def end_of_battery_status(self):
        """'0' if Vdd > 2.25 V and '1' if Vdd < 2.25 V"""
        return (self.user_register >> 6) & 0x1

    def temp_conversion(self, temp_digital):
        """Digital to Analog conversion of temperature data"""
        # Significant digits based on the SHT21 resolution of 0.01 °C
        return round(-46.85 + 175.72 * temp_digital / (2 ** 16 - 1), 2)

    def rhw_conversion(self, rh_digital):
        """Digital to Analog conversion of relative humidity above liquid water (t > 0) data"""
        # Significant digits based on the SHT21 resolution of 0.04 %RH
        rh_analog = round(-6 + 125 * rh_digital / (2 ** 16 - 1), 2)
        # Make sure that relative humidity never returns a 0% value, otherwise the dew point calculation will fail
        rh_analog = 5e-3 if rh_analog < 0.01 else rh_analog
        return rh_analog
