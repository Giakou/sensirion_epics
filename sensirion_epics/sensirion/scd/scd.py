#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parent class for SCDxy sensors from Sensirion
"""

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

    def rhi_conversion(self, rhw):
        """Calculate relative humidity from data"""
        # Significant digits based on the SHT21 resolution of 0.04 %RH
        rh_analog = round(rhw * math.exp(cu.WT['water']['beta'] * self.t / (cu.WT['water']['lambda']))
                          / math.exp(cu.WT['ice']['beta'] * self.t / (cu.WT['ice']['lambda'])), 2)
        # Make sure that relative humidity never returns a 0% value, otherwise the dew point calculation will fail
        rh_analog = 5e-3 if rh_analog < 0.01 else rh_analog
        return rh_analog
