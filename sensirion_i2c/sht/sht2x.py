#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SHT2x Python wrapper library of smbus2
"""

import functools

import sensirion_i2c.sht.utils.conversion_utils as conversion_utils
import sensirion_i2c.utils.log_utils as log_utils
import sensirion_i2c.sht.sht as sht


class SHT2x(sht.SHT):

    def __init__(self):
        super.__init__()
