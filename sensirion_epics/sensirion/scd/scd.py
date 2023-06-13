#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parent class for SCDxy sensors from Sensirion
"""

import struct
import math

import sensirion_epics.sensirion.sensirion_base as sensirion
import sensirion_epics.sensirion.sht.utils.conversion_utils as cu
import sensirion_epics.utils.log_utils as log_utils

logger = log_utils.get_logger()


class SCD(sensirion.SensirionI2C):
    """SCD class"""
    def __init__(self):
        """Constructor"""
        super().__init__()
        self.co2 = None
        self.t = None
        self.rh = None
        self.dp = None

    @sensirion.calculate_crc
    def read_measurement(self):
        """Readout single measurement during continuous measurement mode and signal conversion to physical values"""
        # The measurement data consists of 18 bytes (4 for each measurement value and 2 for each checksum)
        self.read_data_i2c(18)
        co2_uint32 = self.buffer[0] << 24 | self.buffer[1] << 16 | self.buffer[3] << 8 | self.buffer[4]
        # CO2 in ppm
        self.co2 = struct.unpack('f', struct.pack('I', co2_uint32))[0]
        temp_uint32 = self.buffer[6] << 24 | self.buffer[7] << 16 | self.buffer[9] << 8 | self.buffer[10]
        # Temperature in °C
        self.t = struct.unpack('f', struct.pack('I', temp_uint32))[0]
        # Relative humidity in %
        rh_uint32 = self.buffer[12] << 24 | self.buffer[13] << 16 | self.buffer[15] << 8 | self.buffer[16]
        rhw = struct.unpack('f', struct.pack('I', rh_uint32))[0]
        self.rh = rhw if self.t >= 0 else self.rhi_conversion(rhw)
        # Dew point in °C
        self.dp = cu.dew_point(self.t, self.rh)

    # FIXME: Not tested!
    @sensirion.calculate_crc
    def _sn(self, cmd):
        """Output of the serial number"""
        self.write_data_i2c(cmd)
        self.read_data_i2c(33)
        return self.buffer[:31]

    def rhi_conversion(self, rhw):
        """Calculate relative humidity from data"""
        # Significant digits based on the SHT21 resolution of 0.04 %RH
        rh_analog = round(rhw * math.exp(cu.WT['water']['beta'] * self.t / (cu.WT['water']['lambda']))
                          / math.exp(cu.WT['ice']['beta'] * self.t / (cu.WT['ice']['lambda'])), 2)
        # Make sure that relative humidity never returns a 0% value, otherwise the dew point calculation will fail
        rh_analog = 1e-3 if rh_analog < 0.01 else rh_analog
        return rh_analog
