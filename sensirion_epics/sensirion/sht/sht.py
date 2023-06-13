#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import abc
import math

import sensirion_epics.sensirion_i2c.sensirion_i2c as sensirion
import sensirion_epics.sensirion_i2c.sht.utils.conversion_utils as cu
import sensirion_epics.utils.log_utils as log_utils

logger = log_utils.get_logger()


class SHT(sensirion.Sensirion):

    def __init__(self):
        super().__init__()

        self.t = None
        self.rh = None
        self.dp = None

    @abc.abstractmethod
    def temp_conversion(self, *args):
        pass

    @abc.abstractmethod
    def rhw_conversion(self, *args):
        pass

    def rhi_conversion(self, rhw):
        """Calculate relative humidity from data"""
        # Significant digits based on the SHT21 resolution of 0.04 %RH
        rh_analog = round(rhw * math.exp(cu.WT['water']['beta'] * self.t / (cu.WT['water']['lambda']))
                          / math.exp(cu.WT['ice']['beta'] * self.t / (cu.WT['ice']['lambda'])), 2)
        # Make sure that relative humidity never returns a 0% value, otherwise the dew point calculation will fail
        rh_analog = 1e-3 if rh_analog < 0.01 else rh_analog
        return rh_analog

    @sensirion.calculate_crc
    def read_measurement(self):
        """Readout data for Periodic Mode or ART feature and update the properties"""
        # The measurement data consists of 6 bytes (2 for each measurement value and 1 for each checksum)
        self.read_data_i2c(6)
        temp_digital = self.buffer[0] << 8 | self.buffer[1]
        self.t = self.temp_conversion(temp_digital)
        rh_digital = self.buffer[3] << 8 | self.buffer[4]
        rhw = self.rhw_conversion(rh_digital)
        self.rh = rhw if self.t >= 0 else self.rhi_conversion(rhw)
        self.dp = cu.dew_point(self.t, self.rh)

    @sensirion.calculate_crc
    def _sn(self, cmd):
        """Output of the serial number"""
        self.write_data_i2c(cmd)
        self.read_data_i2c(6)
        return (self.buffer[0] << 24) + (self.buffer[1] << 16) + (self.buffer[3] << 8) + self.buffer[4]
