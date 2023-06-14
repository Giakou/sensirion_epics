#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parent class for SHT sensors from Sensirion
"""

import abc
import math

import sensirion_epics.sensirion.sensirion_base as sensirion
import sensirion_epics.sensirion.sht.utils.conversion_utils as cu
import sensirion_epics.utils.log_utils as log_utils

logger = log_utils.get_logger()


class SHT(sensirion.SensirionI2C):
    """SHT class"""
    def __init__(self):
        super().__init__()

        self.t = None
        self.rh = None
        self.dp = None

    @abc.abstractmethod
    def temp_conversion(self, *args):
        """Digital to Analog conversion of temperature data"""
        pass

    @abc.abstractmethod
    def rhw_conversion(self, *args):
        """Digital to Analog conversion of relative humidity above liquid water (t > 0) data"""
        pass

    @abc.abstractmethod
    def read_measurement(self):
        """Readout measurement data"""
        pass

    def rhi_conversion(self, rhw):
        """Convert relative humidity above liquid water (t > 0) to relative humidity above ice (t < 0)"""
        # Significant digits based on the SHT21 resolution of 0.04 %RH
        rh_analog = round(rhw * math.exp(cu.MC['water']['beta'] * self.t / (cu.MC['water']['lambda']))
                          / math.exp(cu.MC['ice']['beta'] * self.t / (cu.MC['ice']['lambda'])), 2)
        # Make sure that relative humidity never returns a 0% value, otherwise the dew point calculation will fail
        rh_analog = 1e-3 if rh_analog < 0.01 else rh_analog
        return rh_analog

    @sensirion.calculate_crc
    def _sn(self, cmd):
        """Output of the serial number"""
        self.write_data_i2c(cmd, wait=0.003)
        self.read_data_i2c(6)
        return (self.buffer[0] << 24) + (self.buffer[1] << 16) + (self.buffer[3] << 8) + self.buffer[4]
