#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SHT2x Python wrapper library of smbus2
"""

import functools

import utils.conversion_utils as cu
import sensirion_i2c.utils.log_utils as lu
import sht


class SHT2x(sht.SHT):

    def __init__(self):
        super.__init__()
